"""Deterministic grade conversion.

Rule of the project: a grade is only converted with the rule the programme itself
states. If the rule is not stated and the scales differ, the answer is
INSUFFICIENT information - we never pick a formula ourselves.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from ..schemas import Criterion, Degree, GradeRule, GradeScale, Label

UK_ORDER = ["third", "lower_second", "upper_second", "first"]
DEFAULT_MAX = {GradeScale.CGPA_4: 4.0, GradeScale.CGPA_5: 5.0, GradeScale.PERCENTAGE: 100.0}
CONVERSION_DIR = Path(__file__).resolve().parents[3] / "data" / "conversion_tables"


def modified_bavarian(value: float, n_max: float, n_min: float) -> float:
    """German grade = 1 + 3 * (Nmax - Nd) / (Nmax - Nmin), clipped to [1.0, 4.0].

    Nmax = best possible grade, Nmin = lowest passing grade, Nd = the student's grade.
    Rounded to 2 decimals; some universities truncate to one decimal, so check the
    programme's own wording when a student is right at the threshold.
    """
    if n_max == n_min:
        raise ValueError("Nmax and Nmin must differ")
    g = 1 + 3 * (n_max - value) / (n_max - n_min)
    return round(min(max(g, 1.0), 4.0), 2)


def _meets(value: float, threshold: float, scale: GradeScale) -> bool:
    if scale == GradeScale.GERMAN:          # lower is better
        return value <= threshold + 1e-9
    return value >= threshold - 1e-9


def _uk_meets(student_class: str, min_class: str) -> bool:
    return UK_ORDER.index(student_class) >= UK_ORDER.index(min_class)


def load_wes_table(scale: GradeScale) -> Optional[list[dict]]:
    """Bands copied by the team from the official WES table, e.g.
    data/conversion_tables/wes_percentage.yaml -> [{min: 70, gpa: 4.0}, ...]."""
    path = CONVERSION_DIR / f"wes_{scale.value}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    return sorted(data["bands"], key=lambda b: -b["min"])


def evaluate_grade(c: Criterion, d: Optional[Degree]) -> tuple[Label, str, str]:
    """Return (label, reason, rule_used) for a min_grade criterion."""
    rule = c.grade_rule or GradeRule.NOT_STATED
    if d is None:
        return Label.INSUFFICIENT, "No degree found in the profile for this grade requirement.", rule.value
    if d.grade_value is None and d.uk_class is None:
        return Label.INSUFFICIENT, "The profile does not state a grade for this degree.", rule.value

    s_scale = d.grade_scale

    # 1. UK classes on both sides
    if c.uk_class_min and d.uk_class:
        ok = _uk_meets(d.uk_class, c.uk_class_min)
        return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                f"Degree class {d.uk_class} vs required {c.uk_class_min}.", "same_scale")

    if d.grade_value is None:
        return Label.INSUFFICIENT, "Only a degree class is known and the requirement is numeric.", rule.value

    # 2. same scale: no conversion needed, whatever the stated rule
    if c.grade_scale is not None and s_scale == c.grade_scale and c.grade_min_value is not None:
        ok = _meets(d.grade_value, c.grade_min_value, s_scale)
        return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                f"{d.grade_value} vs required {c.grade_min_value} on the same scale ({s_scale.value}).",
                "same_scale")

    # 3. a programme-stated threshold for the student's own scale
    if rule in (GradeRule.PROGRAMME_TABLE, GradeRule.UK_CLASS_MAPPING, GradeRule.PERCENTAGE_THRESHOLD):
        for t in c.thresholds:
            if t.scale == s_scale:
                ok = _meets(d.grade_value, t.min_value, s_scale)
                return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                        f"{d.grade_value} vs programme threshold {t.min_value} for {s_scale.value}.",
                        rule.value)
        return (Label.INSUFFICIENT,
                f"The programme gives no threshold for the {s_scale.value if s_scale else 'unknown'} scale.",
                rule.value)

    # 4. modified Bavarian formula -> German grade
    if rule == GradeRule.MODIFIED_BAVARIAN:
        if c.grade_min_value is None:
            return Label.INSUFFICIENT, "German grade threshold not stated.", rule.value
        n_max = d.grade_scale_max or DEFAULT_MAX.get(s_scale)
        n_min = d.grade_scale_min_pass
        if n_max is None or n_min is None or d.grade_value is None:
            return (Label.INSUFFICIENT,
                    "Modified Bavarian formula needs the best and the minimum passing grade of the student's scale.",
                    rule.value)
        g = modified_bavarian(d.grade_value, n_max, n_min)
        ok = g <= c.grade_min_value + 1e-9
        return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                f"{d.grade_value}/{n_max} (min pass {n_min}) converts to German {g}; required {c.grade_min_value} or better.",
                rule.value)

    # 5. WES table
    if rule == GradeRule.WES_GPA:
        bands = load_wes_table(s_scale) if s_scale else None
        if not bands or c.grade_min_value is None:
            return Label.INSUFFICIENT, "No WES conversion table available for this scale.", rule.value
        gpa = next((b["gpa"] for b in bands if d.grade_value >= b["min"]), 0.0)
        ok = gpa >= c.grade_min_value - 1e-9
        return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                f"{d.grade_value} ({s_scale.value}) is WES GPA {gpa}; required {c.grade_min_value}.", rule.value)

    return (Label.INSUFFICIENT,
            "Scales differ and the programme states no conversion rule, so the grade cannot be checked.",
            rule.value)
