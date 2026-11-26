"""Group second-experiment failures by cause (Table A8 / errors slide).

Usage:
    python scripts/error_groups_v2.py --name v2_chal
    python scripts/error_groups_v2.py --name v2_chal --model gpt-oss-20b

Reads runs/<name>/predictions.jsonl (latest record per model/system/pair) and
writes runs/<name>/error_analysis_v2.md with failure counts per cause for S2 and
S2-oracle. The rules mirror the manual grouping used in the report.
"""
import argparse
import collections
import json
from pathlib import Path

LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
CAUSES = {
    "A": "Missing English score treated as not met",
    "B": "Semantic judge too strict (field or motivation)",
    "C": "Both track rules applied",
    "D": "Short degree below the credit minimum",
    "E": "Criterion missed or too lenient in extraction",
    "F": "Test threshold not extracted",
    "G": "Only admission or document items (nothing to judge)",
    "H": "Model call failed",
    "I": "Other insufficient-information verdict",
}


def cause(rec):
    pred = rec["pred"]
    crits = rec.get("criteria", [])
    if pred == "NE":
        ne = [c for c in crits if c["label"] == "not_eligible"]
        t = ne[0]["type"] if ne else "?"
        if t == "english_test" and "No accepted" in ne[0]["reason"]:
            return "A"
        if t in ("degree_field", "other"):
            return "B"
        if t == "years_of_education":
            return "C"
        if t == "min_credits":
            return "D"
        return "I"
    if pred == "E":
        return "E"
    ii = [c for c in crits if c["label"] == "insufficient_info"]
    if not ii:
        return "G"
    if any("error" in c["reason"].lower() or "failed" in c["reason"].lower() for c in ii):
        return "H"
    if "No minimum" in ii[0]["reason"]:
        return "F"
    return "I"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--model", default="gemini-flash-lite")
    args = ap.parse_args()
    run = Path("runs") / args.name
    latest = {}
    for line in open(run / "predictions.jsonl", encoding="utf-8"):
        r = json.loads(line)
        latest[(r["model"], r["system"], r["pair_id"])] = r

    systems = ["S2", "S2-oracle"]
    counts = {s: collections.Counter() for s in systems}
    examples = {}
    for (m, s, pid), r in sorted(latest.items()):
        if m != args.model or s not in systems or r["gold"] == r["pred"]:
            continue
        c = cause(r)
        counts[s][c] += 1
        examples.setdefault(c, f"{pid} {r['programme_id']} gold {r['gold']} -> {r['pred']}")

    lines = [f"# Error analysis v2: {args.name} / {args.model}", "",
             "| Cause | S2 | S2 on gold criteria | Example |", "|---|---|---|---|"]
    for k in LABELS:
        if counts["S2"][k] or counts["S2-oracle"][k]:
            lines.append(f"| {CAUSES[k]} | {counts['S2'][k]} | {counts['S2-oracle'][k]} | {examples.get(k, '')} |")
    lines.append(f"| **Total** | **{sum(counts['S2'].values())}** | **{sum(counts['S2-oracle'].values())}** | |")
    out = run / "error_analysis_v2.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()