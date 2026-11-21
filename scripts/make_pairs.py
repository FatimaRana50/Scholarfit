"""Sample profile-programme pairs for labelling (ScholarElig).

  python scripts/make_pairs.py --n 200 --dev-frac 0.2 --seed 1

Programmes are split into dev and test BEFORE sampling, so no programme seen while
writing prompts appears in the test set. Pairs are stratified by scholarship family.
Writes data/labels/pairs.csv; annotators fill the label columns (see the guideline).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = ["min_grade", "years_of_education", "min_credits", "degree_level", "degree_field", "age_limit",
         "nationality", "english_test", "work_experience", "other"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--dev-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--profiles", default="data/profiles/synthetic")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    progs = [json.loads(l) for l in (ROOT / "data/programmes/programmes.jsonl").read_text().splitlines() if l.strip()]
    profiles = sorted(p.stem for p in (ROOT / args.profiles).glob("*.json"))
    by_fam = defaultdict(list)
    for p in progs:
        by_fam[p["family"]].append(p["programme_id"])

    split = {}
    for fam, ids in by_fam.items():
        rng.shuffle(ids)
        n_dev = max(1, round(len(ids) * args.dev_frac)) if len(ids) > 1 else 0
        for j, pid in enumerate(ids):
            split[pid] = "dev" if j < n_dev else "test"

    fams = sorted(by_fam)
    pairs, seen = [], set()
    while len(pairs) < args.n and len(seen) < len(progs) * len(profiles):
        fam = fams[len(pairs) % len(fams)]                 # round-robin over families
        prog = rng.choice(by_fam[fam])
        prof = rng.choice(profiles)
        if (prof, prog) in seen:
            continue
        seen.add((prof, prog))
        pairs.append((prof, prog, fam))

    out = ROOT / "data/labels/pairs.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "split", "profile_id", "programme_id", "family", "annotator"]
                   + [f"label_{t}" for t in TYPES] + ["overall", "evidence", "notes"])
        for i, (prof, prog, fam) in enumerate(pairs, 1):
            w.writerow([f"pair{i:04d}", split[prog], prof, prog, fam, ""] + [""] * len(TYPES) + ["", "", ""])
    n_test = sum(split[p] == "test" for _, p, _ in pairs)
    print(f"wrote {len(pairs)} pairs ({n_test} test, {len(pairs) - n_test} dev) to {out}")


if __name__ == "__main__":
    main()
