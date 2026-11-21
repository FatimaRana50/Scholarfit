"""One client for every model (OpenAI, Gemini, Ollama) via the OpenAI-compatible API.

Features needed by the rubric:
* JSON output validated with Pydantic, one retry that feeds the validation error back
* every call logged to runs/llm_calls.jsonl with latency, tokens and cost (D5)
* a disk cache so re-running an evaluation does not pay twice (disable with --no-cache)
* a mock mode (SCHOLARFIT_MOCK=1) so the whole pipeline can be tested offline
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from ..config import RUNS, model_cfg

T = TypeVar("T", bound=BaseModel)
LOG_FILE = RUNS / "llm_calls.jsonl"
CACHE_DIR = RUNS / "cache"
MOCKS: dict[str, Callable[[list[dict]], str]] = {}   # component -> fake response (tests only)
_last_call: dict[str, float] = {}                      # model -> time of last request (rate limiting)
_tok_hist: dict[str, list] = {}                        # model -> [(time, tokens)] in the last minute
_JSON_FALLBACKS: dict[str, int] = {}                   # model -> times JSON mode was dropped after a 400


def _throttle(cfg: dict, est_tokens: int = 0):
    """Wait so we stay under the free tier's requests-per-minute AND tokens-per-minute limits."""
    if os.environ.get("SCHOLARFIT_MOCK") == "1":
        return
    name = cfg["name"]
    rpm = cfg.get("rpm") or 0
    if rpm > 0:
        wait = 60.0 / rpm - (time.time() - _last_call.get(name, 0))
        if wait > 0:
            time.sleep(wait)
    tpm = cfg.get("tpm") or 0
    if tpm > 0 and est_tokens:
        while True:
            now = time.time()
            hist = [(t, n) for t, n in _tok_hist.get(name, []) if now - t < 60]
            _tok_hist[name] = hist
            used = sum(n for _, n in hist)
            if not hist or used + est_tokens <= tpm:
                break
            time.sleep(max(1.0, 60 - (now - hist[0][0]) + 0.5))
    _last_call[name] = time.time()


def _record_tokens(cfg: dict, n: int):
    if cfg.get("tpm"):
        _tok_hist.setdefault(cfg["name"], []).append((time.time(), n))


def _retry_after(r) -> float:
    try:
        return float(r.headers.get("retry-after", ""))
    except ValueError:
        m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", r.text)
        return (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else 0.0


@dataclass
class CallMeta:
    component: str
    model: str
    latency_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Optional[float] = 0.0
    attempts: int = 0
    cached: bool = False
    ok: bool = True
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)


class LLMError(RuntimeError):
    pass


def _cost(cfg: dict, pt: int, ct: int) -> Optional[float]:
    pin, pout = cfg.get("price_in_per_m"), cfg.get("price_out_per_m")
    if pin is None or pout is None:
        return None
    return (pt * pin + ct * pout) / 1_000_000


def _log(meta: CallMeta, run_tag: str):
    RUNS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), "run": run_tag, **{k: v for k, v in meta.__dict__.items()}}
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _raw_call(cfg: dict, messages: list[dict], temperature: float, seed: Optional[int]) -> tuple[str, dict]:
    if os.environ.get("SCHOLARFIT_MOCK") == "1":
        from . import mocks  # noqa: F401  (registers fake responses)
        comp = messages[0].get("_component", "")
        fn = MOCKS.get(comp)
        if fn is None:
            raise LLMError(f"No mock registered for component '{comp}'")
        return fn(messages), {"prompt_tokens": 100, "completion_tokens": 50}
    body = {"model": cfg["model"], "temperature": temperature,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages]}
    if cfg.get("json_mode", True):
        body["response_format"] = {"type": "json_object"}
    if seed is not None and cfg.get("supports_seed", True):   # Gemini's OpenAI endpoint rejects "seed"
        body["seed"] = seed
    body.update(cfg.get("extra_body") or {})          # e.g. reasoning_effort for gpt-oss (same for every system)
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    est = sum(len(m["content"]) for m in messages) // 4 + int(cfg.get("est_output_tokens", 800))
    for backoff in (0, 5, 15, 30, 60, 60, 60):
        if backoff:
            time.sleep(backoff)
        _throttle(cfg, est)
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code == 400 and "json_validate_failed" in r.text and "response_format" in body:
            # Groq rejects the whole reply when JSON mode output fails its own check (common with
            # gpt-oss). Same prompt, same settings, JSON mode off; our parser + Pydantic check it instead.
            body = {k: v for k, v in body.items() if k != "response_format"}
            _JSON_FALLBACKS[cfg["name"]] = _JSON_FALLBACKS.get(cfg["name"], 0) + 1
            _record_tokens(cfg, est)
            _throttle(cfg, est)
            r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code == 429:
            low = r.text.lower()
            if "per day" in low or "(tpd)" in low or "(rpd)" in low or "resource_exhausted" in low:
                raise LLMError(f"HTTP 429 daily quota: {r.text[:300]}")   # waiting will not help
            _record_tokens(cfg, est)
            time.sleep(_retry_after(r))
            continue
        if r.status_code in (500, 502, 503, 504):
            continue
        if r.status_code != 200:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        usage = dict(data.get("usage") or {})
        _record_tokens(cfg, int(usage.get("total_tokens") or est))
        usage["json_fallback"] = "response_format" not in body and cfg.get("json_mode", True)
        return data["choices"][0]["message"]["content"], usage
    raise LLMError(f"HTTP {r.status_code} after retries: {r.text[:300]}")


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start >= 0 and end > start else text


def chat_json(messages: list[dict], schema: Type[T], component: str, model: str,
              temperature: float = 0.0, seed: Optional[int] = None, use_cache: bool = True,
              run_tag: str = "") -> tuple[T, CallMeta]:
    """Call the model and return a validated Pydantic object plus call metadata."""
    cfg = model_cfg(model)
    meta = CallMeta(component=component, model=model)
    key_parts = [cfg["model"], messages, temperature, seed, schema.__name__]
    if cfg.get("extra_body"):
        key_parts.append(cfg["extra_body"])          # a different reasoning setting must not reuse old answers
    key_src = json.dumps(key_parts, sort_keys=True, default=str)
    key = hashlib.sha256(key_src.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.json"
    if use_cache and cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        meta.cached = True
        meta.latency_s, meta.prompt_tokens, meta.completion_tokens = cached["latency_s"], cached["pt"], cached["ct"]
        meta.cost_usd = _cost(cfg, meta.prompt_tokens, meta.completion_tokens)
        _log(meta, run_tag)
        return schema.model_validate(cached["obj"]), meta

    msgs = [dict(m) for m in messages]
    msgs[0]["_component"] = component
    last_err = None
    t0 = time.perf_counter()
    for attempt in (1, 2):
        meta.attempts = attempt
        try:
            text, usage = _raw_call(cfg, msgs, temperature, seed)
        except (LLMError, requests.RequestException) as e:
            meta.ok, meta.error = False, str(e)[:300]
            meta.latency_s = time.perf_counter() - t0
            _log(meta, run_tag)
            raise LLMError(str(e)) from e
        meta.prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        meta.completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        if usage.get("json_fallback"):
            meta.extra["json_fallback"] = True
        try:
            obj = schema.model_validate_json(_extract_json(text))
            break
        except ValidationError as e:
            last_err = e
            msgs = msgs + [{"role": "assistant", "content": text},
                           {"role": "user", "content": "Your JSON did not match the schema. Errors:\n"
                            f"{str(e)[:1500]}\nReturn corrected JSON only."}]
    else:
        meta.ok, meta.error = False, f"schema invalid after retry: {str(last_err)[:300]}"
        meta.latency_s = time.perf_counter() - t0
        meta.cost_usd = _cost(cfg, meta.prompt_tokens, meta.completion_tokens)
        _log(meta, run_tag)
        raise LLMError(meta.error)

    meta.latency_s = time.perf_counter() - t0
    meta.cost_usd = _cost(cfg, meta.prompt_tokens, meta.completion_tokens)
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"obj": obj.model_dump(mode="json"), "latency_s": meta.latency_s,
                                          "pt": meta.prompt_tokens, "ct": meta.completion_tokens}))
    _log(meta, run_tag)
    return obj, meta