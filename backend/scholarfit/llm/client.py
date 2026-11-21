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


def _throttle(cfg: dict):
    rpm = cfg.get("rpm") or 0
    if rpm <= 0 or os.environ.get("SCHOLARFIT_MOCK") == "1":
        return
    wait = 60.0 / rpm - (time.time() - _last_call.get(cfg["name"], 0))
    if wait > 0:
        time.sleep(wait)
    _last_call[cfg["name"]] = time.time()


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
    if cfg.get("reasoning_effort"):
        body["reasoning_effort"] = cfg["reasoning_effort"]
    if seed is not None:
        body["seed"] = seed
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    for backoff in (0, 5, 15, 30, 60):
        if backoff:
            time.sleep(backoff)
        _throttle(cfg)
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code in (429, 500, 502, 503, 504):
            continue
        if r.status_code != 200:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        return data["choices"][0]["message"]["content"], data.get("usage", {})
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
    key_src = json.dumps([cfg["model"], messages, temperature, seed, schema.__name__], sort_keys=True, default=str)
    key = hashlib.sha256(key_src.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{key}.json"
    if use_cache and cache_file.exists():
        cached = json.loads(cache_file.read_text())
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
