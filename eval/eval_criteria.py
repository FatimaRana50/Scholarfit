"""Evaluate criteria extraction separately from the rule engine (supervisor point 3).

  python eval/eval_criteria.py --models gemini-flash gpt-oss-20b --context retrieved full

Each extracted criterion is matched to a gold criterion of the same programme and type.
Reports: recall (gold criteria found), precision (extracted criteria that match gold),
criterion-level accuracy (type + every key value correct), grade-rule accuracy,
handling-mode accuracy, citation support rate (quote really in the text), latency, cost.
"""
from __future__ import annotations

import argparse
import csv
import time
from statistics import mean

from common import ROOT, load_gold_criteria, load_programmes
from metrics import percentile

from scholarfit.llm.client import LLMError
from scholarfit.pipelines.criteria import extract_criteria
from scholarfit.retrieval import quote_in_text

KEY_FIELDS = {
    "min_grade": ["grade_min_value", "grade_scale", "uk_class_min", "grade_rule"],
    "years_of_education": ["min_years"], "min_credits": ["min_ects"],
    "degree_level": ["required_level", "final_year_allowed"], "degree_field": [],
    "age_limit": ["max_age", "born_on_or_after", "age_reference_date"],
    "nationality": ["nationalities_allowed", "nationalities_excluded"],
    "english_test": ["english_min_scores", "english_min_band", "english_waiver_medium_of_instruction"],
    "work_experience": ["min_work_months"], "deadline": ["deadline"], "other": [],
}


def norm(v):
    if isinstance(v, list):
        return sorted(str(x).lower() for x in v)
    if isinstance(v, dict):
        return {k.lower(): float(x) for k, x in v.items()}
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def field_ok(g, p, f):
    return norm(getattr(g, f)) == norm(getattr(p, f)) or (getattr(g, f) in (None, [], {}) and getattr(p, f) in (None, [], {}))


def match(gold, pred):
    pairs, used = [], set()
    for g in gold:
        cands = [(j, p) for j, p in enumerate(pred) if j not in used and p.type == g.type]
        if not cands:
            pairs.append((g, None))
            continue
        j, p = max(cands, key=lambda jp: sum(field_ok(g, jp[1], f) for f in KEY_FIELDS[g.type.value]))
        used.add(j)
        pairs.append((g, p))
    return pairs, len(pred) - len(used)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gemini-flash"])
    ap.add_argument("--context", nargs="+", default=["retrieved"])
    ap.add_argument("--split-programmes", default=None, help="optional file with test programme ids, one per line")
    args = ap.parse_args()
    progs = load_programmes(ROOT / "data/programmes/programmes.jsonl")
    gold = load_gold_criteria(ROOT / "data/labels/criteria_gold.jsonl")
    ids = sorted(gold)
    if args.split_programmes:
        keep = set(open(args.split_programmes).read().split())
        ids = [i for i in ids if i in keep]
    out = ROOT / "runs" / "criteria_eval"
    out.mkdir(parents=True, exist_ok=True)
    summary, fails = [], []
    for model in args.models:
        for ctx in args.context:
            found = correct = rule_ok = rule_n = hand_ok = n_gold = n_pred = extra = cited = 0
            lat, costs = [], []
            for pid in ids:
                t0 = time.perf_counter()
                try:
                    pred, meta = extract_criteria(progs[pid], model, context=ctx, run_tag=f"criteria_eval:{ctx}")
                    costs.append(meta.cost_usd)
                except LLMError as e:
                    pred = []
                    costs.append(None)
                    fails.append([model, ctx, pid, "ALL", "", f"error: {e}"[:200]])
                lat.append(time.perf_counter() - t0)
                g = [c for c in gold[pid] if c.type.value != "deadline"]
                p = [c for c in pred if c.type.value != "deadline"]
                pairs, n_extra = match(g, p)
                n_gold += len(g); n_pred += len(p); extra += n_extra
                cited += sum(quote_in_text(c.source_quote, progs[pid].text) for c in p)
                for gc, pc in pairs:
                    if pc is None:
                        fails.append([model, ctx, pid, gc.type.value, gc.text, "MISSED"])
                        continue
                    found += 1
                    ok = all(field_ok(gc, pc, f) for f in KEY_FIELDS[gc.type.value])
                    correct += ok
                    hand_ok += gc.handling == pc.handling
                    if gc.type.value == "min_grade":
                        rule_n += 1
                        rule_ok += gc.grade_rule == pc.grade_rule
                    if not ok:
                        bad = [f"{f}: gold={getattr(gc, f)} pred={getattr(pc, f)}" for f in KEY_FIELDS[gc.type.value]
                               if not field_ok(gc, pc, f)]
                        fails.append([model, ctx, pid, gc.type.value, gc.text, "; ".join(bad)])
            summary.append({"model": model, "context": ctx, "programmes": len(ids), "gold_criteria": n_gold,
                            "recall": round(found / n_gold, 4) if n_gold else None,
                            "precision": round((n_pred - extra) / n_pred, 4) if n_pred else None,
                            "criterion_accuracy": round(correct / n_gold, 4) if n_gold else None,
                            "handling_accuracy": round(hand_ok / found, 4) if found else None,
                            "grade_rule_accuracy": round(rule_ok / rule_n, 4) if rule_n else None,
                            "citation_supported": round(cited / n_pred, 4) if n_pred else None,
                            "p50_latency_s": round(percentile(lat, 50), 2), "p95_latency_s": round(percentile(lat, 95), 2),
                            "mean_cost_usd": None if any(c is None for c in costs) else round(mean(costs), 5)})
    with (out / "summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    with (out / "failures.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "context", "programme_id", "type", "gold_text", "problem"])
        w.writerows(fails)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
