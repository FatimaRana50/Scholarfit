from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from scholarfit.schemas import Criterion, Profile, Programme  # noqa: E402

TYPES = ["min_grade", "years_of_education", "min_credits", "degree_level", "degree_field", "age_limit",
         "nationality", "english_test", "work_experience", "other"]


def load_programmes(path: str | Path) -> dict[str, Programme]:
    out = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            p = Programme(**json.loads(line))
            out[p.programme_id] = p
    return out


def load_profiles(folder: str | Path) -> dict[str, Profile]:
    return {p.stem: Profile(**json.loads(p.read_text())) for p in Path(folder).glob("*.json")}


def load_pairs(path: str | Path, split: str | None = None, labelled_only: bool = True) -> list[dict]:
    rows = list(csv.DictReader(Path(path).open()))
    if split and split != "all":
        rows = [r for r in rows if r["split"] == split]
    if labelled_only:
        rows = [r for r in rows if r.get("overall", "").strip()]
    return rows


def load_gold_criteria(path: str | Path) -> dict[str, list[Criterion]]:
    out: dict[str, list[Criterion]] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            pid = d.pop("programme_id")
            out.setdefault(pid, []).append(Criterion(**d))
    return out
