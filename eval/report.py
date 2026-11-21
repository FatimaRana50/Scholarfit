"""Turn experiment predictions into the results shown in the demo (Stage D).

  python eval/report.py --name a3_first [--baseline B1 --treatment S2]

Writes runs/<name>/report.md, summary.csv, per_type.csv, failures.csv and charts (PNG):
* metrics per system and model, mean +- std over runs                    (D2, D6)
* paired McNemar test and bootstrap CI for the baseline vs treatment     (D3, D6)
* per criterion type breakdown (RQ2)
* latency p50/p95 and cost per pair from the running pipeline            (D5)
* failures.csv with an auto-suggested cause column to finish by hand      (D4)
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from statistics import mean, pstdev

from common import ROOT, TYPES
from metrics import bootstrap_diff, eligibility_metrics, holm, mcnemar, percentile

KEYS = ["accuracy", "macro_f1", "false_eligible_rate", "false_not_eligible_rate", "under_abstention",
        "risky_under_abstention", "over_abstention"]


def fmt(xs):
    xs = [x for x in xs if x == x]
    if not xs:
        return "n/a"
    return f"{mean(xs):.3f} ± {pstdev(xs):.3f}" if len(xs) > 1 else f"{xs[0]:.3f}"


def suggest_cause(r: dict) -> str:
    if r.get("error"):
        return "pipeline error"
    diffs = [t for t, g in r["gold_types"].items() if g not in ("NA", "") and r["pred_types"].get(t, "NA") != g]
    missing = [t for t in diffs if r["pred_types"].get(t, "NA") == "NA"]
    if missing:
        return f"criterion missed: {', '.join(missing)}"
    if diffs:
        return f"wrong verdict on: {', '.join(diffs)}"
    return "overall combination"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--baseline", default="B1")
    ap.add_argument("--treatment", default="S2")
    args = ap.parse_args()
    d = ROOT / "runs" / args.name
    recs = [json.loads(l) for l in (d / "predictions.jsonl").read_text().splitlines() if l.strip()]

    groups = defaultdict(lambda: defaultdict(list))      # (system, model) -> run -> records
    for r in recs:
        groups[(r["system"], r["model"])][r["run"]].append(r)

    # ---- overall metrics, mean +- std over runs
    summary_rows, lines = [], [f"# Results: {args.name}\n"]
    lines.append(f"{len({r['pair_id'] for r in recs})} pairs, runs per condition: "
                 f"{max(r['run'] for r in recs) + 1}\n")
    lines.append("| System | Model | " + " | ".join(KEYS) + " | p50 latency (s) | p95 latency (s) | cost / pair (USD) | errors |")
    lines.append("|" + "---|" * (len(KEYS) + 6))
    for (sysname, model), runs in sorted(groups.items()):
        per_run = [eligibility_metrics([r["gold"] for r in rs], [r["pred"] for r in rs]) for rs in runs.values()]
        allr = [r for rs in runs.values() for r in rs]
        lat = [r["latency_s"] for r in allr if r["latency_s"] is not None]
        costs = [r["cost_usd"] for r in allr]
        cost = "n/a (set prices)" if any(c is None for c in costs) else f"{mean(costs):.5f}"
        errs = sum(bool(r["error"]) for r in allr)
        row = {"system": sysname, "model": model, **{k: fmt([m[k] for m in per_run]) for k in KEYS},
               "p50_latency_s": f"{percentile(lat, 50):.2f}", "p95_latency_s": f"{percentile(lat, 95):.2f}",
               "cost_per_pair_usd": cost, "errors": errs}
        summary_rows.append(row)
        lines.append(f"| {sysname} | {model} | " + " | ".join(row[k] for k in KEYS) +
                     f" | {row['p50_latency_s']} | {row['p95_latency_s']} | {cost} | {errs} |")

    # ---- confusion matrix of run 0 per condition
    lines.append("\n## Confusion matrices (run 0; rows = gold, columns = predicted)\n")
    for (sysname, model), runs in sorted(groups.items()):
        rs = runs[min(runs)]
        cm = eligibility_metrics([r["gold"] for r in rs], [r["pred"] for r in rs])["confusion"]
        lines.append(f"**{sysname} / {model}**\n\n| gold \\ pred | E | NE | II |\n|---|---|---|---|")
        for g in ("E", "NE", "II"):
            lines.append(f"| {g} | {cm[g]['E']} | {cm[g]['NE']} | {cm[g]['II']} |")
        lines.append("")

    # ---- baseline vs treatment: McNemar + bootstrap on false-eligible indicator
    lines.append(f"\n## {args.treatment} vs {args.baseline} (paired, per run)\n")
    lines.append("| Model | Run | Accuracy diff | McNemar p | FER diff [95% CI] |\n|---|---|---|---|---|")
    pvals = {}
    for model in sorted({m for _, m in groups}):
        A, B = groups.get((args.treatment, model)), groups.get((args.baseline, model))
        if not A or not B:
            continue
        for run in sorted(set(A) & set(B)):
            a = {r["pair_id"]: r for r in A[run]}
            b = {r["pair_id"]: r for r in B[run]}
            ids = sorted(set(a) & set(b))
            ca = [a[i]["pred"] == a[i]["gold"] for i in ids]
            cb = [b[i]["pred"] == b[i]["gold"] for i in ids]
            t = mcnemar(ca, cb)
            pvals[f"{model}/run{run}"] = t["p_value"]
            ne = [i for i in ids if a[i]["gold"] == "NE"]
            if ne:
                fa = [float(a[i]["pred"] == "E") for i in ne]
                fb = [float(b[i]["pred"] == "E") for i in ne]
                diff, lo, hi = bootstrap_diff(fa, fb)
                fer = f"{diff:+.3f} [{lo:+.3f}, {hi:+.3f}]"
            else:
                fer = "no NE pairs"
            lines.append(f"| {model} | {run} | {mean(ca) - mean(cb):+.3f} | {t['p_value']:.4f} | {fer} |")
    if pvals:
        adj = holm(pvals)
        lines.append("\nHolm-adjusted p-values: " + ", ".join(f"{k}: {v:.4f}" for k, v in adj.items()))

    # ---- per criterion type (RQ2): accuracy where gold type is labelled
    lines.append("\n## Accuracy by criterion type (all runs pooled; a missed criterion counts as wrong)\n")
    type_rows = []
    head = "| System | Model | " + " | ".join(TYPES) + " |"
    lines += [head, "|" + "---|" * (len(TYPES) + 2)]
    for (sysname, model), runs in sorted(groups.items()):
        cells, row = [], {"system": sysname, "model": model}
        for t in TYPES:
            pairs = [(r["gold_types"].get(t), r["pred_types"].get(t, "NA")) for rs in runs.values() for r in rs
                     if r["gold_types"].get(t) in ("E", "NE", "II")]
            acc = mean(g == p for g, p in pairs) if pairs else None
            row[t] = "" if acc is None else f"{acc:.3f} (n={len(pairs)})"
            cells.append(row[t] or "-")
        type_rows.append(row)
        lines.append(f"| {sysname} | {model} | " + " | ".join(cells) + " |")

    # ---- latency / cost per component from the call log
    log = ROOT / "runs" / "llm_calls.jsonl"
    if log.exists():
        calls = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        calls = [c for c in calls if str(c.get("run", "")).startswith(args.name) and not c.get("cached")]
        comp = defaultdict(list)
        for c in calls:
            comp[(c["component"], c["model"])].append(c)
        lines.append("\n## Model calls by component (uncached calls only)\n")
        lines.append("| Component | Model | Calls | p50 latency (s) | p95 latency (s) | Mean tokens in/out | Failure rate | Retry rate |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for (cname, model), cs in sorted(comp.items()):
            lat = [c["latency_s"] for c in cs]
            lines.append(f"| {cname} | {model} | {len(cs)} | {percentile(lat, 50):.2f} | {percentile(lat, 95):.2f} | "
                         f"{mean(c['prompt_tokens'] for c in cs):.0f}/{mean(c['completion_tokens'] for c in cs):.0f} | "
                         f"{mean(not c['ok'] for c in cs):.2%} | {mean(c['attempts'] > 1 for c in cs):.2%} |")

    # ---- failures for error analysis (run 0)
    fails = [r for r in recs if r["run"] == 0 and r["pred"] != r["gold"]]
    with (d / "failures.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "model", "pair_id", "family", "gold", "pred", "suggested_cause", "final_cause",
                    "planned_fix", "criteria_reasons"])
        for r in fails:
            w.writerow([r["system"], r["model"], r["pair_id"], r["family"], r["gold"], r["pred"], suggest_cause(r),
                        "", "", " | ".join(f"{c['type']}={c['label']}: {c['reason']}" for c in r["criteria"])[:900]])
    lines.append(f"\n{len(fails)} failures in run 0 written to failures.csv - group at least 10 by cause and add planned fixes.")

    for name, rows in (("summary.csv", summary_rows), ("per_type.csv", type_rows)):
        if rows:
            with (d / name).open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    (d / "report.md").write_text("\n".join(lines))
    charts(d, groups)
    print("\n".join(lines[:12 + len(groups)]))
    print(f"\nfull report: {d / 'report.md'}")


def charts(d, groups):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    conds = sorted(groups)
    for key, title, fname in (("false_eligible_rate", "False-eligible rate (lower is better)", "fer.png"),
                              ("macro_f1", "Macro-F1 (higher is better)", "macro_f1.png")):
        vals, errs = [], []
        for c in conds:
            xs = [eligibility_metrics([r["gold"] for r in rs], [r["pred"] for r in rs])[key] for rs in groups[c].values()]
            xs = [x for x in xs if x == x] or [0.0]
            vals.append(mean(xs))
            errs.append(pstdev(xs) if len(xs) > 1 else 0)
        fig, ax = plt.subplots(figsize=(max(5, 1.3 * len(conds)), 3.6))
        ax.bar([f"{s}\n{m}" for s, m in conds], vals, yerr=errs, capsize=4, color="#4C72B0")
        ax.set_title(title)
        ax.set_ylim(0, 1)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(d / fname, dpi=160)
        plt.close(fig)


if __name__ == "__main__":
    main()
