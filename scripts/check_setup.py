"""Check that keys and models work:  python scripts/check_setup.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import os  # noqa: E402

from pydantic import BaseModel  # noqa: E402

from scholarfit.llm.client import chat_json  # noqa: E402


class Ping(BaseModel):
    ok: bool


for model, env in (("gemini-flash", "GEMINI_API_KEY"), ("gpt-oss-20b", "GROQ_API_KEY")):
    if not os.environ.get(env):
        print(f"[missing] {env} is not set in .env  ->  {model} will not work")
        continue
    try:
        out, meta = chat_json([{"role": "system", "content": 'Reply with JSON {"ok": true}.'},
                               {"role": "user", "content": "ping"}], Ping, component="setup_check",
                              model=model, use_cache=False, run_tag="setup")
        print(f"[ok] {model} answered in {meta.latency_s:.1f}s")
    except Exception as e:
        print(f"[error] {model}: {e}")
