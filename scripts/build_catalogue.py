"""Load programmes into the app database and extract their criteria once per snapshot.

  python scripts/build_catalogue.py --model gemini-flash           # all programmes
  python scripts/build_catalogue.py --gold                         # use hand-checked CriteriaGold instead
  python scripts/build_catalogue.py --demo                         # fictional fixtures, for a dry run

Criteria with an unsupported citation, low confidence or handling=manual_check are saved
as 'needs_review' and only shown to students after a curator approves them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from scholarfit import store  # noqa: E402
from scholarfit.schemas import Criterion, Programme  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-flash")
    ap.add_argument("--gold", action="store_true")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    src = ROOT / ("backend/tests/fixtures/programmes.jsonl" if args.demo else "data/programmes/programmes.jsonl")
    progs = [Programme(**json.loads(l)) for l in src.read_text().splitlines() if l.strip()]
    gold = {}
    if args.gold:
        for l in (ROOT / "data/labels/criteria_gold.jsonl").read_text().splitlines():
            d = json.loads(l)
            gold.setdefault(d.pop("programme_id"), []).append(Criterion(**d))
    from scholarfit.pipelines.criteria import extract_criteria
    for p in progs:
        store.upsert_programme(p)
        if args.gold:
            crits = gold.get(p.programme_id, [])
            for c in crits:
                c.confidence = 1.0
            store.save_criteria(p.programme_id, crits, "gold")
        else:
            crits, meta = extract_criteria(p, args.model, run_tag="catalogue")
            store.save_criteria(p.programme_id, crits, args.model)
        print(f"{p.programme_id}: {len(crits)} criteria")
    print(f"catalogue ready in {store.DB_PATH}")


if __name__ == "__main__":
    main()
