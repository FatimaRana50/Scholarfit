"""Metrics for ScholarFit (no external dependencies beyond numpy/scipy).

Label codes: E = eligible, NE = not eligible, II = insufficient information.
How each outcome is scored (supervisor point 6):
  false-eligible rate (FER)     P(pred = E  | gold = NE)        primary metric
  false-not-eligible rate (FNER) P(pred = NE | gold = E)         missed opportunities
  under-abstention              P(pred in {E, NE} | gold = II)  counted as an error
  risky under-abstention        P(pred = E | gold = II)         the dangerous part of it
  over-abstention               P(pred = II | gold in {E, NE})  softer cost, reported apart
"""
from __future__ import annotations

import math
import random
from collections import Counter

import numpy as np
from scipy.stats import binomtest

LABELS = ["E", "NE", "II"]
TO_CODE = {"eligible": "E", "not_eligible": "NE", "insufficient_info": "II", "manual_check": "II",
           "E": "E", "NE": "NE", "II": "II", "NA": "NA"}
SEVERITY = {"NE": 3, "II": 2, "E": 1}


def code(x: str) -> str:
    return TO_CODE.get((x or "").strip(), (x or "").strip())


def confusion(gold: list[str], pred: list[str]) -> dict:
    m = {g: {p: 0 for p in LABELS} for g in LABELS}
    for g, p in zip(gold, pred):
        if g in m and p in m[g]:
            m[g][p] += 1
    return m


def _rate(num: int, den: int):
    return num / den if den else float("nan")


def eligibility_metrics(gold: list[str], pred: list[str]) -> dict:
    gold, pred = [code(g) for g in gold], [code(p) for p in pred]
    n = len(gold)
    cm = confusion(gold, pred)
    f1s = []
    for lab in LABELS:
        tp = cm[lab][lab]
        fp = sum(cm[g][lab] for g in LABELS if g != lab)
        fn = sum(cm[lab][p] for p in LABELS if p != lab)
        prec = _rate(tp, tp + fp)
        rec = _rate(tp, tp + fn)
        f1 = 0.0 if (tp == 0) else 2 * prec * rec / (prec + rec)
        if tp + fn > 0:                      # only labels present in gold count toward macro-F1
            f1s.append(f1)
    n_ne, n_e, n_ii = (sum(g == x for g in gold) for x in ("NE", "E", "II"))
    return {
        "n": n,
        "accuracy": _rate(sum(g == p for g, p in zip(gold, pred)), n),
        "macro_f1": float(np.mean(f1s)) if f1s else float("nan"),
        "false_eligible_rate": _rate(cm["NE"]["E"], n_ne),
        "false_not_eligible_rate": _rate(cm["E"]["NE"], n_e),
        "under_abstention": _rate(cm["II"]["E"] + cm["II"]["NE"], n_ii),
        "risky_under_abstention": _rate(cm["II"]["E"], n_ii),
        "over_abstention": _rate(cm["E"]["II"] + cm["NE"]["II"], n_e + n_ne),
        "confusion": cm,
    }


def combine_types(labels: list[str]) -> str:
    """Several criteria of one type -> the most severe label."""
    labs = [code(l) for l in labels if code(l) in SEVERITY]
    return max(labs, key=lambda l: SEVERITY[l]) if labs else "NA"


def cohen_kappa(a: list[str], b: list[str]) -> float:
    pairs = [(x, y) for x, y in zip(a, b) if x and y]
    if not pairs:
        return float("nan")
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def mcnemar(correct_a: list[bool], correct_b: list[bool]) -> dict:
    """Exact McNemar test on paired per-item correctness."""
    b = sum(x and not y for x, y in zip(correct_a, correct_b))   # A right, B wrong
    c = sum(y and not x for x, y in zip(correct_a, correct_b))   # B right, A wrong
    p = binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0
    return {"a_only": b, "b_only": c, "p_value": p}


def bootstrap_diff(values_a: list[float], values_b: list[float], stat=np.mean, n_boot: int = 2000,
                   seed: int = 0) -> tuple[float, float, float]:
    """Paired bootstrap CI for stat(a) - stat(b). Returns (diff, low, high) at 95%."""
    rng = random.Random(seed)
    idx = list(range(len(values_a)))
    a, b = np.array(values_a, float), np.array(values_b, float)
    diffs = []
    for _ in range(n_boot):
        s = [rng.choice(idx) for _ in idx]
        diffs.append(stat(a[s]) - stat(b[s]))
    return float(stat(a) - stat(b)), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def percentile(xs: list[float], q: float) -> float:
    xs = sorted(x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x)))
    if not xs:
        return float("nan")
    return float(np.percentile(xs, q))
