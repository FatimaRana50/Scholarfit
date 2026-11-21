"""Inter-annotator agreement (Cohen's kappa) on the double-labelled pairs.

  python eval/agreement.py data/labels/pairs_annotatorA.csv data/labels/pairs_annotatorB.csv

Both files have the pairs.csv columns; only pair_ids present and labelled in both are used.
"""
from __future__ import annotations

import csv
import sys

from common import TYPES
from metrics import cohen_kappa, code


def main(a_path, b_path):
    A = {r["pair_id"]: r for r in csv.DictReader(open(a_path)) if r.get("overall")}
    B = {r["pair_id"]: r for r in csv.DictReader(open(b_path)) if r.get("overall")}
    ids = sorted(set(A) & set(B))
    print(f"{len(ids)} pairs labelled by both annotators\n")
    print(f"{'item':22s} kappa   agreement  n")
    for col in ["overall"] + [f"label_{t}" for t in TYPES]:
        a = [code(A[i][col]) for i in ids if A[i].get(col) and B[i].get(col)]
        b = [code(B[i][col]) for i in ids if A[i].get(col) and B[i].get(col)]
        if not a:
            continue
        agree = sum(x == y for x, y in zip(a, b)) / len(a)
        print(f"{col:22s} {cohen_kappa(a, b):5.3f}   {agree:6.1%}   {len(a)}")
    dis = [i for i in ids if code(A[i]["overall"]) != code(B[i]["overall"])]
    print(f"\nDisagreements on overall ({len(dis)}): {', '.join(dis)}  -> discuss, update the guideline, re-label")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
