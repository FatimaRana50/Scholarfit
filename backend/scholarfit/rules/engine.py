"""The deterministic rule engine (the symbolic half of S2).

Takes a profile and a list of criteria in the general schema and returns a verdict
per criterion and an overall verdict. No language model is called here, except via
the optional `semantic_judge` callback for criteria marked SEMANTIC.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from ..schemas import (Criterion, CriterionType, CriterionVerdict, DegreeLevel,
                       EligibilityResult, Handling, Label, Profile)

__all__ = ["evaluate", "combine", "resolve_groups", "target_level", "missing_requirements", "age_on"]
from .grades import evaluate_grade

LEVEL_ORDER = [DegreeLevel.SECONDARY, DegreeLevel.INTERMEDIATE, DegreeLevel.BACHELOR,
               DegreeLevel.MASTER, DegreeLevel.PHD]
TERTIARY = {DegreeLevel.BACHELOR, DegreeLevel.MASTER, DegreeLevel.PHD}
ECTS_PER_YEAR = 60  # ECTS Users' Guide: one full-time academic year = 60 ECTS

SemanticJudge = Callable[[Criterion, Profile], tuple[Label, str]]

COUNTRY_ALIASES = {"pakistani": "pakistan", "islamic republic of pakistan": "pakistan",
                   "uk": "united kingdom", "usa": "united states", "us": "united states"}


def _norm_country(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    x = x.strip().lower()
    return COUNTRY_ALIASES.get(x, x)


def age_on(dob: date, ref: date) -> int:
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def target_level(p: Profile) -> DegreeLevel:
    """The degree the student applies for: as stated, else the next above the highest completed one."""
    if p.target_level:
        return p.target_level
    done = [d.level for d in p.degrees if d.level in TERTIARY and d.completed]
    if not done:
        return DegreeLevel.BACHELOR if not any(d.level in TERTIARY for d in p.degrees) else DegreeLevel.MASTER
    top = max(done, key=LEVEL_ORDER.index)
    return DegreeLevel.PHD if top in (DegreeLevel.MASTER, DegreeLevel.PHD) else DegreeLevel.MASTER


def _completed_tertiary(p: Profile, include_in_progress: bool):
    return [d for d in p.degrees if d.level in TERTIARY and (d.completed or include_in_progress)]


# --------------------------------------------------------------------------- per type
def _years_of_education(c: Criterion, p: Profile):
    if c.min_years is None:
        return Label.INSUFFICIENT, "Required years of education not stated.", None
    has_12 = any(d.level == DegreeLevel.INTERMEDIATE for d in p.degrees)
    if not has_12:
        return Label.INSUFFICIENT, "Pre-university schooling (12 years) not found in the profile.", None

    def total(include_in_progress: bool):
        degs = _completed_tertiary(p, include_in_progress)
        if any(d.duration_years is None for d in degs):
            return None
        return 12 + sum(d.duration_years for d in degs)

    done = total(False)
    if done is None:
        return Label.INSUFFICIENT, "Duration of a degree is missing.", None
    if done >= c.min_years:
        return Label.ELIGIBLE, f"{done:g} years of education vs {c.min_years:g} required.", "12 + degree durations"
    with_current = total(True)
    if with_current is not None and with_current >= c.min_years:
        if c.final_year_allowed:
            return (Label.CONDITIONAL, f"{with_current:g} years once the degree in progress is completed; "
                    "final-year applicants allowed, so the degree must be completed before the programme starts.",
                    "12 + degree durations")
        return Label.INSUFFICIENT, f"Only {done:g} completed years; {with_current:g} after the degree in progress.", "12 + degree durations"
    return Label.NOT_ELIGIBLE, f"{done:g} years of education vs {c.min_years:g} required.", "12 + degree durations"


def _min_credits(c: Criterion, p: Profile):
    if c.min_ects is None:
        return Label.INSUFFICIENT, "Required credits not stated.", None
    degs = _completed_tertiary(p, include_in_progress=bool(c.final_year_allowed))
    best = None
    for d in degs:
        ects = d.ects if d.ects is not None else (d.duration_years * ECTS_PER_YEAR if d.duration_years else None)
        if ects is not None:
            best = max(best or 0, ects)
    if best is None:
        return Label.INSUFFICIENT, "No degree with known duration or credits.", None
    ok = best >= c.min_ects
    return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
            f"{best:g} ECTS-equivalent vs {c.min_ects:g} required.", "60 ECTS per full-time year")


def _degree_level(c: Criterion, p: Profile):
    if c.required_level is None:
        return Label.INSUFFICIENT, "Required degree level not stated.", None
    need = LEVEL_ORDER.index(c.required_level)
    done = [d for d in p.degrees if LEVEL_ORDER.index(d.level) >= need and d.completed]
    if done:
        return Label.ELIGIBLE, f"Holds a completed {done[0].level.value} degree.", None
    current = [d for d in p.degrees if LEVEL_ORDER.index(d.level) >= need and not d.completed]
    if current:
        if c.final_year_allowed is True:
            return (Label.CONDITIONAL, "Degree in progress; final-year applicants are allowed if they graduate "
                    "before the programme starts.", None)
        if c.final_year_allowed is False:
            return Label.NOT_ELIGIBLE, "Degree not yet completed; final-year applicants not allowed.", None
        return Label.INSUFFICIENT, "Degree in progress and the call does not say if final-year students may apply.", None
    return Label.NOT_ELIGIBLE, f"No {c.required_level.value} degree in the profile.", None


def _age(c: Criterion, p: Profile, deadline: Optional[date]):
    if p.date_of_birth is None:
        return Label.INSUFFICIENT, "Date of birth not in the profile.", None
    if c.born_on_or_after:
        ok = p.date_of_birth >= c.born_on_or_after
        return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
                f"Born {p.date_of_birth}; must be born on or after {c.born_on_or_after}.", "date comparison")
    if c.max_age is None:
        return Label.INSUFFICIENT, "Age limit not stated.", None
    ref = c.age_reference_date or deadline
    if ref is None:
        return Label.INSUFFICIENT, "No reference date for the age limit.", None
    a = age_on(p.date_of_birth, ref)
    ok = a <= c.max_age
    return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
            f"Age {a} on {ref} vs maximum {c.max_age}.", "age on reference date")


def _nationality(c: Criterion, p: Profile):
    nat = _norm_country(p.nationality)
    if nat is None:
        return Label.INSUFFICIENT, "Nationality not in the profile.", None
    allowed = {_norm_country(x) for x in c.nationalities_allowed}
    excluded = {_norm_country(x) for x in c.nationalities_excluded}
    if nat in excluded:
        return Label.NOT_ELIGIBLE, f"{p.nationality} is excluded.", None
    if allowed and nat not in allowed:
        return Label.NOT_ELIGIBLE, f"{p.nationality} is not among eligible nationalities.", None
    if allowed or excluded:
        return Label.ELIGIBLE, f"{p.nationality} is eligible.", None
    return Label.INSUFFICIENT, "Nationality rule not stated.", None


def _english(c: Criterion, p: Profile):
    waiver = c.english_waiver_medium_of_instruction
    if waiver and p.english_medium_instruction:
        return Label.ELIGIBLE, "Waived: bachelor taught in English.", "waiver"
    if not c.english_min_scores:
        return Label.INSUFFICIENT, "No minimum test score stated.", None
    accepted = {k.lower(): v for k, v in c.english_min_scores.items()}
    bands = {k.lower(): v for k, v in c.english_min_band.items()}
    seen_below = False
    for t in p.english_tests:
        key = t.test.lower()
        if key not in accepted:
            continue
        if t.overall < accepted[key]:
            seen_below = True
            continue
        if key in bands:
            if t.min_band is None:
                return Label.INSUFFICIENT, f"{t.test} sub-scores needed (min {bands[key]}).", None
            if t.min_band < bands[key]:
                seen_below = True
                continue
        return Label.ELIGIBLE, f"{t.test} {t.overall} meets {accepted[key]}.", "score comparison"
    if waiver and p.english_medium_instruction is None:
        return Label.INSUFFICIENT, "No accepted score; a medium-of-instruction waiver may apply but is not shown.", None
    if seen_below:
        return Label.NOT_ELIGIBLE, "Test score below the minimum.", "score comparison"
    return Label.NOT_ELIGIBLE, "No accepted English test score in the profile.", None


def _work(c: Criterion, p: Profile):
    if c.min_work_months is None:
        return Label.INSUFFICIENT, "Required work experience not stated.", None
    if p.work_experience_months is None:
        return Label.INSUFFICIENT, "Work experience not in the profile.", None
    ok = p.work_experience_months >= c.min_work_months
    return (Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE,
            f"{p.work_experience_months} months vs {c.min_work_months} required.", "month comparison")


def _grade_degree(c: Criterion, p: Profile):
    if c.applies_to_level:
        return p.highest(c.applies_to_level)
    # default: the most recent tertiary degree with a grade
    tert = [d for d in p.degrees if d.level in TERTIARY]
    return max(tert, key=lambda d: LEVEL_ORDER.index(d.level)) if tert else None


# --------------------------------------------------------------------------- engine
GROUP_ORDER = [Label.ELIGIBLE, Label.CONDITIONAL, Label.INSUFFICIENT, Label.NOT_ELIGIBLE]


def combine(verdicts: list[CriterionVerdict]) -> Label:
    scored = [v.label for v in verdicts if v.label != Label.MANUAL]
    if not scored:
        return Label.INSUFFICIENT
    if Label.NOT_ELIGIBLE in scored:
        return Label.NOT_ELIGIBLE
    if Label.INSUFFICIENT in scored:
        return Label.INSUFFICIENT
    if Label.CONDITIONAL in scored:
        return Label.CONDITIONAL
    return Label.ELIGIBLE


def resolve_groups(criteria: list[Criterion], verdicts: list[CriterionVerdict]) -> None:
    """Alternatives (same any_of id): the group is met if any member is met."""
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(criteria):
        if c.any_of and verdicts[i].label != Label.MANUAL:
            groups.setdefault(c.any_of, []).append(i)
    for idx in groups.values():
        if len(idx) < 2:
            continue
        best = min((verdicts[i].label for i in idx), key=GROUP_ORDER.index)
        winner = next(i for i in idx if verdicts[i].label == best)
        for i in idx:
            v = verdicts[i]
            if i != winner:
                v.reason = f"Alternative to another requirement ({best.value}); own check: {v.reason}"
            v.label = best


def evaluate(programme_id: str, criteria: list[Criterion], profile: Profile,
             semantic_judge: Optional[SemanticJudge] = None, today: Optional[date] = None,
             system: str = "S2") -> EligibilityResult:
    deadline = next((c.deadline for c in criteria if c.type == CriterionType.DEADLINE and c.deadline), None)
    target = target_level(profile)
    kept = [c for c in criteria if c.type != CriterionType.DEADLINE and (c.track is None or c.track == target)]
    out: list[CriterionVerdict] = []
    for c in kept:
        rule = None
        if c.type == CriterionType.DOCUMENT:
            label, reason = Label.MANUAL, f"Document to prepare: {c.text or 'see the call'}."
        elif c.type == CriterionType.ADMISSION:
            label, reason = Label.MANUAL, ("Admission requirement of the host university, separate from scholarship "
                                           "eligibility: confirm with the university.")
        elif c.handling == Handling.MANUAL:
            label, reason = Label.MANUAL, "Checked by a person (selection stage or not verifiable from a CV)."
        elif c.handling == Handling.SEMANTIC or c.type in (CriterionType.DEGREE_FIELD, CriterionType.OTHER):
            if semantic_judge is None:
                label, reason = Label.INSUFFICIENT, "Needs a semantic judgement; no judge configured."
            else:
                label, reason = semantic_judge(c, profile)
                rule = "semantic judge"
        elif c.type == CriterionType.MIN_GRADE:
            label, reason, rule = evaluate_grade(c, _grade_degree(c, profile))
        elif c.type == CriterionType.YEARS_OF_EDUCATION:
            label, reason, rule = _years_of_education(c, profile)
        elif c.type == CriterionType.MIN_CREDITS:
            label, reason, rule = _min_credits(c, profile)
        elif c.type == CriterionType.DEGREE_LEVEL:
            label, reason, rule = _degree_level(c, profile)
        elif c.type == CriterionType.AGE_LIMIT:
            label, reason, rule = _age(c, profile, deadline)
        elif c.type == CriterionType.NATIONALITY:
            label, reason, rule = _nationality(c, profile)
        elif c.type == CriterionType.ENGLISH_TEST:
            label, reason, rule = _english(c, profile)
        elif c.type == CriterionType.WORK_EXPERIENCE:
            label, reason, rule = _work(c, profile)
        else:
            label, reason = Label.INSUFFICIENT, "Unsupported criterion type."
        if label == Label.ELIGIBLE and c.condition:
            label, reason = Label.CONDITIONAL, f"{reason} Condition: {c.condition}"
        out.append(CriterionVerdict(criterion_id=c.criterion_id, type=c.type, label=label,
                                    reason=reason, rule_used=rule, citation=c.source_quote))
    resolve_groups(kept, out)
    today = today or date.today()
    return EligibilityResult(programme_id=programme_id, profile_id=profile.profile_id, system=system,
                             overall=combine(out), criteria=out,
                             deadline_open=(deadline >= today) if deadline else None)


# --------------------------------------------------------------------------- what the student still needs
def missing_requirements(result: EligibilityResult, criteria: list[Criterion]) -> list[dict]:
    """Plain-language to-do list for one programme (feature F8): what is not met, undecided,
    conditional, to be checked by a person, or a document to prepare."""
    by_id = {c.criterion_id: c for c in criteria if c.criterion_id}
    todo = []
    for v in result.criteria:
        c = by_id.get(v.criterion_id)
        what = (c.text if c and c.text else v.type.value.replace("_", " "))
        if v.label == Label.NOT_ELIGIBLE:
            kind, action = "not_met", f"Not met: {what}. {v.reason}"
        elif v.label == Label.INSUFFICIENT:
            kind, action = "missing_info", f"Add the missing information or check the call: {what}. {v.reason}"
        elif v.label == Label.CONDITIONAL:
            kind, action = "condition", f"Make sure this condition is met before the programme starts: {v.reason}"
        elif v.label == Label.MANUAL:
            kind = "document" if v.type == CriterionType.DOCUMENT else "manual"
            action = v.reason if v.type in (CriterionType.DOCUMENT, CriterionType.ADMISSION) else f"Checked by a person: {what}."
        else:
            continue
        todo.append({"kind": kind, "type": v.type.value, "action": action, "evidence": v.citation})
    order = {"not_met": 0, "missing_info": 1, "condition": 2, "document": 3, "manual": 4}
    return sorted(todo, key=lambda t: order[t["kind"]])
