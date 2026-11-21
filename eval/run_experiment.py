"""Research experiment: eligibility systems on labelled ScholarElig pairs.

Assignment 3 first experiment (B1 vs S2, one API + one local model, 3 runs):
  python eval/run_experiment.py --name a3_first --systems B1 S2 --models gemini-flash gpt-oss-20b --runs 3

Assignment 4 full experiment:
  python eval/run_experiment.py --name a4_full --systems B0 B1 B2 S1 S2 --oracle --models ... --runs 5

Every run differs in its seed; at temperature 0 the API's own non-determinism is what
varies. Results go to runs/<name>/predictions.jsonl, then: python eval/report.py --name <name>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import date

from common import ROOT, load_gold_criteria, load_pairs, load_profiles, load_programmes
from metrics import combine_types, code

from scholarfit.pipelines.systems import SYSTEMS, run_s2


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "no-git"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--systems", nargs="+", default=["B1", "S2"])
    ap.add_argument("--models", nargs="+", default=["gemini-flash"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--split", default="test", choices=["test", "dev", "all"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--context", default="retrieved", choices=["retrieved", "full"])
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--oracle", action="store_true", help="also run S2 on gold criteria (S2-oracle)")
    ap.add_argument("--today", default=None, help="reference date for 'today' (default: programme snapshot date)")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--pairs", default=str(ROOT / "data/labels/pairs.csv"))
    ap.add_argument("--programmes", default=str(ROOT / "data/programmes/programmes.jsonl"))
    ap.add_argument("--profiles", default=str(ROOT / "data/profiles/synthetic"))
    ap.add_argument("--gold-criteria", default=str(ROOT / "data/labels/criteria_gold.jsonl"))
    args = ap.parse_args()

    progs, profs = load_programmes(args.programmes), load_profiles(args.profiles)
    pairs = load_pairs(args.pairs, args.split)[: args.limit]
    gold_crit = load_gold_criteria(args.gold_criteria) if args.oracle else {}
    out_dir = ROOT / "runs" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps({**vars(args), "git_commit": git_commit(),
                                                     "started": time.ctime(), "n_pairs": len(pairs)}, indent=1))
    pred_file = out_dir / "predictions.jsonl"
    done = set()
    if pred_file.exists():   # resume an interrupted experiment
        for line in pred_file.read_text().splitlines():
            r = json.loads(line)
            done.add((r["run"], r["model"], r["system"], r["pair_id"]))

    systems = list(args.systems) + (["S2-oracle"] if args.oracle else [])
    total = args.runs * len(args.models) * len(systems) * len(pairs)
    k = 0
    with pred_file.open("a") as f:
        for run in range(args.runs):
            for model in args.models:
                for sysname in systems:
                    if sysname == "B0" and model != args.models[0]:
                        continue          # B0 uses no model: run it once
                    for pr in pairs:
                        k += 1
                        key = (run, "none" if sysname == "B0" else model, sysname, pr["pair_id"])
                        if key in done:
                            continue
                        prog, prof = progs[pr["programme_id"]], profs[pr["profile_id"]]
                        today = date.fromisoformat(args.today) if args.today else (prog.snapshot_date or date.today())
                        common = dict(model=model, today=today, context=args.context, temperature=args.temperature,
                                      seed=run, use_cache=not args.no_cache, run_tag=f"{args.name}:{sysname}")
                        if sysname == "S2-oracle":
                            if pr["programme_id"] not in gold_crit:
                                continue
                            res = run_s2(prog, prof, criteria=gold_crit[pr["programme_id"]],
                                         system_name="S2-oracle", **common)
                        else:
                            res = SYSTEMS[sysname](prog, prof, **common)
                        by_type: dict[str, list[str]] = {}
                        for v in res.criteria:
                            by_type.setdefault(v.type.value, []).append(v.label.value)
                        rec = {"run": run, "model": "none" if sysname == "B0" else model, "system": sysname, "pair_id": pr["pair_id"],
                               "profile_id": pr["profile_id"], "programme_id": pr["programme_id"],
                               "family": pr["family"], "gold": code(pr["overall"]), "pred": code(res.overall.value),
                               "gold_types": {t[6:]: code(pr[t]) for t in pr if t.startswith("label_") and pr[t]},
                               "pred_types": {t: combine_types(ls) for t, ls in by_type.items()},
                               "criteria": [v.model_dump(mode="json") for v in res.criteria],
                               "latency_s": res.latency_s, "cost_usd": res.cost_usd, "error": res.error}
                        f.write(json.dumps(rec) + "\n")
                        f.flush()
                        print(f"[{k}/{total}] run{run} {model} {sysname} {pr['pair_id']}: "
                              f"gold={rec['gold']} pred={rec['pred']}" + (f" ERROR {res.error}" if res.error else ""))
    print(f"done -> {pred_file}\nnext: python eval/report.py --name {args.name}")


if __name__ == "__main__":
    main()
