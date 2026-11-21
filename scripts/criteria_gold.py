"""Build CriteriaGold with a human in the loop.

  python scripts/criteria_gold.py draft --model gemini-flash   # LLM draft -> data/labels/criteria_draft.csv
  (annotators correct EVERY row in the CSV, add missing criteria, delete wrong ones,
   and set checked_by to their name; corrections are logged by comparing with the draft)
  python scripts/criteria_gold.py build                       # CSV -> data/labels/criteria_gold.jsonl
  python scripts/criteria_gold.py corrections                 # how often the draft was wrong

Declare the drafting in the AI tool declaration: the draft only saves typing; every
field is checked by a person against the source text before it becomes gold.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from scholarfit.schemas import Criterion, Programme  # noqa: E402

COLS = ["programme_id", "type", "handling", "text", "source_quote", "grade_rule", "grade_min_value", "grade_scale",
        "uk_class_min", "thresholds", "applies_to_level", "min_years", "min_ects", "min_work_months",
        "required_level", "final_year_allowed", "fields", "max_age", "age_reference_date", "born_on_or_after",
        "nationalities_allowed", "nationalities_excluded", "english_min_scores", "english_min_band",
        "english_waiver_medium_of_instruction", "deadline", "checked_by"]
JSON_COLS = {"thresholds", "fields", "nationalities_allowed", "nationalities_excluded", "english_min_scores",
             "english_min_band"}
DRAFT = ROOT / "data/labels/criteria_draft.csv"
EDITED = ROOT / "data/labels/criteria_checked.csv"
GOLD = ROOT / "data/labels/criteria_gold.jsonl"


def load_programmes():
    return [Programme(**json.loads(l)) for l in (ROOT / "data/programmes/programmes.jsonl").read_text().splitlines() if l.strip()]


def to_row(pid: str, c: Criterion) -> dict:
    d = c.model_dump(mode="json")
    row = {"programme_id": pid}
    for k in COLS[1:]:
        v = d.get(k)
        row[k] = json.dumps(v) if k in JSON_COLS else ("" if v is None else v)
    row["checked_by"] = ""
    return row


def draft(model: str, limit: int | None):
    from scholarfit.pipelines.criteria import extract_criteria
    rows = []
    for prog in load_programmes()[:limit]:
        crits, _ = extract_criteria(prog, model)
        rows += [to_row(prog.programme_id, c) for c in crits]
        print(f"{prog.programme_id}: {len(crits)} criteria")
    with DRAFT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    if not EDITED.exists():
        EDITED.write_text(DRAFT.read_text())
    print(f"draft written to {DRAFT}; annotators edit {EDITED}")


def build():
    n = 0
    with EDITED.open() as f, GOLD.open("w") as out:
        for i, row in enumerate(csv.DictReader(f), 1):
            if not row.get("checked_by"):
                raise SystemExit(f"row {i} ({row['programme_id']}) has no checked_by: every row must be checked")
            d = {}
            for k in COLS[1:-1]:
                v = row.get(k, "")
                if v in ("", "null", None):
                    continue
                d[k] = json.loads(v) if k in JSON_COLS else v
            if "final_year_allowed" in d:
                d["final_year_allowed"] = str(d["final_year_allowed"]).lower() == "true"
            if "english_waiver_medium_of_instruction" in d:
                d["english_waiver_medium_of_instruction"] = str(d["english_waiver_medium_of_instruction"]).lower() == "true"
            c = Criterion(**d)
            c.criterion_id = f"{row['programme_id']}-g{i}"
            out.write(json.dumps({"programme_id": row["programme_id"], **c.model_dump(mode="json", exclude_none=True)}) + "\n")
            n += 1
    print(f"{n} gold criteria written to {GOLD}")


def corrections():
    def key(r):
        return (r["programme_id"], r["type"], r["source_quote"][:60])
    d = {key(r): r for r in csv.DictReader(DRAFT.open())}
    e = {key(r): r for r in csv.DictReader(EDITED.open())}
    kept = [k for k in d if k in e]
    changed = sum(any(d[k][c] != e[k][c] for c in COLS[:-1]) for k in kept)
    print(f"draft criteria: {len(d)}; deleted: {len(d) - len(kept)}; added: {len(set(e) - set(d))}; "
          f"edited: {changed}; unchanged: {len(kept) - changed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draft", "build", "corrections"])
    ap.add_argument("--model", default="gemini-flash")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    {"draft": lambda: draft(a.model, a.limit), "build": build, "corrections": corrections}[a.cmd]()
