"""Evaluate CV-to-profile extraction against gold profiles (D1-D5 for this component).

  python eval/eval_cv.py --models gemini-flash gpt-oss-20b          # + the rule-based baseline
  python eval/eval_cv.py --models gemini-flash --cv-dir data/profiles/real   # real CVs, reported apart

Field-level accuracy over every gold field (a value invented where the gold is empty
counts as wrong), schema-valid output rate, latency and cost. Writes
runs/cv_eval/<model>_fields.csv and failures.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean

from common import ROOT
from metrics import percentile

from scholarfit.llm.client import LLMError
from scholarfit.pipelines.cv import extract_profile_llm, extract_profile_rules, read_cv_text
from scholarfit.schemas import Profile

DEG_FIELDS = ["duration_years", "completed", "grade_value", "grade_scale", "grade_scale_max", "grade_scale_min_pass"]
TOP_FIELDS = ["date_of_birth", "nationality", "english_medium_instruction", "work_experience_months"]


DEMONYMS = {"pakistani": "pakistan", "indian": "india", "bangladeshi": "bangladesh", "nepalese": "nepal",
            "nepali": "nepal", "afghan": "afghanistan", "chinese": "china", "iranian": "iran"}


def norm_country(x):
    """The rule engine treats 'Pakistani' and 'Pakistan' as the same country, so the metric does too."""
    if not isinstance(x, str):
        return x
    return DEMONYMS.get(x.strip().lower(), x.strip().lower())


def same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 0.011
        except (TypeError, ValueError):
            return False
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    return a == b


def compare(gold: Profile, pred: Profile) -> list[tuple[str, object, object, bool]]:
    g, p = gold.model_dump(mode="json"), pred.model_dump(mode="json")
    rows = [(f, g.get(f), p.get(f), same(norm_country(g.get(f)), norm_country(p.get(f))) if f == "nationality"
             else same(g.get(f), p.get(f))) for f in TOP_FIELDS]
    for gd in g["degrees"]:
        cands = [d for d in p["degrees"] if d["level"] == gd["level"]]
        pd = cands[0] if len(cands) == 1 else next((d for d in cands if same(d.get("grade_value"), gd.get("grade_value"))),
                                                   cands[0] if cands else {})
        for f in DEG_FIELDS:
            rows.append((f"{gd['level']}.{f}", gd.get(f), pd.get(f), same(gd.get(f), pd.get(f))))
    for gt in g["english_tests"]:
        pt = next((t for t in p["english_tests"] if t["test"].lower().replace(" ", "_") == gt["test"].lower()), {})
        for f in ("overall", "min_band"):
            rows.append((f"{gt['test']}.{f}", gt.get(f), pt.get(f), same(gt.get(f), pt.get(f))))
    if not g["english_tests"]:
        rows.append(("english_tests.none", 0, len(p["english_tests"]), len(p["english_tests"]) == 0))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["gemini-flash"])
    ap.add_argument("--cv-dir", default=str(ROOT / "data/profiles/synthetic"))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    cv_dir = Path(args.cv_dir)
    golds = sorted(cv_dir.glob("*.json"))[: args.limit]
    out = ROOT / "runs" / "cv_eval"
    out.mkdir(parents=True, exist_ok=True)
    summary, failures = [], []
    for model in ["rules-baseline"] + args.models:
        per_field, valid, lat, costs = defaultdict(list), 0, [], []
        for gpath in golds:
            gold = Profile(**json.loads(gpath.read_text(encoding="utf-8")))
            cv = next((cv_dir / f"{gpath.stem}{s}" for s in (".pdf", ".docx", ".txt") if (cv_dir / f"{gpath.stem}{s}").exists()), None)
            if cv is None:
                continue
            text = read_cv_text(cv)
            t0 = time.perf_counter()
            try:
                if model == "rules-baseline":
                    pred = extract_profile_rules(text)
                    cost = 0.0
                else:
                    pred, meta = extract_profile_llm(text, model, use_cache=not args.no_cache, run_tag="cv_eval")
                    cost = meta.cost_usd
                valid += 1
            except LLMError as e:
                pred, cost = Profile(), None
                failures.append({"model": model, "cv": cv.name, "field": "SCHEMA", "gold": "", "pred": str(e)[:200]})
            lat.append(time.perf_counter() - t0)
            costs.append(cost)
            for f, gv, pv, ok in compare(gold, pred):
                per_field[f.split(".", 1)[-1] if "." in f else f].append(ok)
                if not ok:
                    failures.append({"model": model, "cv": cv.name, "field": f, "gold": gv, "pred": pv})
        allv = [x for v in per_field.values() for x in v]
        summary.append({"model": model, "n_cvs": len(golds), "field_accuracy": round(mean(allv), 4) if allv else None,
                        "schema_valid_rate": round(valid / len(golds), 4) if golds else None,
                        "p50_latency_s": round(percentile(lat, 50), 3), "p95_latency_s": round(percentile(lat, 95), 3),
                        "mean_cost_usd": None if any(c is None for c in costs) else round(mean(costs), 6)})
        with (out / f"{model}_fields.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["field", "accuracy", "n"])
            for k, v in sorted(per_field.items()):
                w.writerow([k, round(mean(v), 4), len(v)])
    with (out / "summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    with (out / "failures.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["model", "cv", "field", "gold", "pred"])
        w.writeheader()
        w.writerows(failures)
    for s in summary:
        print(s)
    print(f"details in {out}")


if __name__ == "__main__":
    main()