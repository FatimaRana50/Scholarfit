"""Requirement breakdown for the app (feature F3): one row per criterion with the requirement,
the matching profile value, the engine's verdict in plain words and the evidence quote.
Display only: the verdicts come from scholarfit.rules.engine."""
from __future__ import annotations

from datetime import date
from typing import Optional

from .rules.engine import LEVEL_ORDER, TERTIARY, age_on, target_level
from .schemas import (Criterion, CriterionType, CriterionVerdict, Degree, EligibilityResult, Label,
                      Profile)

RESULT_TEXT = {
    Label.ELIGIBLE: "Met",
    Label.NOT_ELIGIBLE: "Not met",
    Label.CONDITIONAL: "Conditionally met",
    Label.INSUFFICIENT: "Not enough information",
    Label.MANUAL: "Checked by a person",
}
NOT_IN_PROFILE = "Not in your profile"


def _deg(d: Degree) -> str:
    name = d.title or (f"{d.level.value} in {d.field}" if d.field else d.level.value)
    status = "completed" if d.completed else "in progress" if d.completed is False else "status unknown"
    return f"{name} ({status})"


def _grade(d: Optional[Degree]) -> str:
    if d is None or d.grade_value is None:
        return "No grade in your profile"
    scale = (d.grade_scale.value if d.grade_scale else "scale unknown").replace("_", " ")
    out = f"{d.grade_value:g}"
    if d.grade_scale_max:
        out += f" / {d.grade_scale_max:g}"
    out += f" ({scale}"
    if d.grade_scale_min_pass is not None:
        out += f", pass {d.grade_scale_min_pass:g}"
    return out + f") - {_deg(d)}"


def profile_value(c: Criterion, p: Profile, today: date) -> str:
    tert = [d for d in p.degrees if d.level in TERTIARY]
    t = c.type
    if t == CriterionType.MIN_GRADE:
        if c.applies_to_level:
            d = p.highest(c.applies_to_level)
        else:
            d = max(tert, key=lambda x: LEVEL_ORDER.index(x.level)) if tert else None
        return _grade(d)
    if t == CriterionType.YEARS_OF_EDUCATION:
        school = "12 years school" if any(d.level.value == "intermediate" for d in p.degrees) else "school years not found"
        degs = [f"{_deg(d)}, {d.duration_years:g} yrs" if d.duration_years else _deg(d) for d in tert]
        return " + ".join([school] + degs)
    if t == CriterionType.MIN_CREDITS:
        if not tert:
            return NOT_IN_PROFILE
        return "; ".join(f"{_deg(d)}: " + (f"{d.ects:g} ECTS" if d.ects else
                                           f"{d.duration_years:g} yrs" if d.duration_years else "length unknown")
                         for d in tert)
    if t == CriterionType.DEGREE_LEVEL:
        return "; ".join(_deg(d) for d in tert) or NOT_IN_PROFILE
    if t == CriterionType.DEGREE_FIELD:
        return "; ".join(d.field or d.title or d.level.value for d in tert) or NOT_IN_PROFILE
    if t == CriterionType.AGE_LIMIT:
        if not p.date_of_birth:
            return NOT_IN_PROFILE
        return f"Born {p.date_of_birth} (age {age_on(p.date_of_birth, today)} today)"
    if t == CriterionType.NATIONALITY:
        return p.nationality or NOT_IN_PROFILE
    if t == CriterionType.ENGLISH_TEST:
        parts = [f"{x.test} {x.overall:g}" + (f" (lowest band {x.min_band:g})" if x.min_band is not None else "")
                 for x in p.english_tests]
        if p.english_medium_instruction:
            parts.append("bachelor taught in English")
        return "; ".join(parts) or NOT_IN_PROFILE
    if t == CriterionType.WORK_EXPERIENCE:
        return f"{p.work_experience_months} months" if p.work_experience_months is not None else NOT_IN_PROFILE
    if c.track:
        return f"Applying for {target_level(p).value}"
    return "-"


def result_text(v: CriterionVerdict) -> str:
    if v.type == CriterionType.ADMISSION:
        return "Checked by a person: admission requirement of the host university"
    if v.type == CriterionType.DOCUMENT:
        return "Document to prepare"
    return RESULT_TEXT.get(v.label, v.label.value)


def breakdown(result: EligibilityResult, criteria: list[Criterion], profile: Profile, today: date) -> list[dict]:
    """The verdicts of `result`, enriched with the requirement text and the student's value."""
    by_id = {c.criterion_id: c for c in criteria if c.criterion_id}
    rows = []
    for v in result.criteria:
        c = by_id.get(v.criterion_id)
        row = v.model_dump(mode="json")
        row.update(requirement=(c.text if c and c.text else v.type.value.replace("_", " ")),
                   your_profile=profile_value(c, profile, today) if c else "-",
                   result=result_text(v),
                   condition=c.condition if c else None,
                   alternative_group=c.any_of if c else None)
        rows.append(row)
    return rows
