"""Paths and model registry. Models are listed in config/models.yaml so that the
experiment can switch between an API model and a local model without code changes."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]          # repository root
DATA = ROOT / "data"
RUNS = ROOT / "runs"
PROMPTS = Path(__file__).resolve().parent / "prompts"
MODELS_FILE = ROOT / "config" / "models.yaml"


def _load_dotenv():
    """Read KEY=VALUE lines from the repository's .env file (no extra package needed)."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.split(" #", 1)[0].strip().strip('"').strip("'")
        if val:
            os.environ.setdefault(key.strip(), val)


_load_dotenv()


def load_models() -> dict:
    return yaml.safe_load(MODELS_FILE.read_text())["models"]


def model_cfg(name: str) -> dict:
    models = load_models()
    if name not in models:
        raise KeyError(f"Unknown model '{name}'. Known: {list(models)}")
    cfg = dict(models[name])
    cfg["name"] = name
    cfg["api_key"] = os.environ.get(cfg.get("api_key_env", ""), "") if cfg.get("api_key_env") else "ollama"
    return cfg


def default_model() -> str:
    return os.environ.get("SCHOLARFIT_MODEL", "gemini-flash")


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text()
