"""The five eligibility systems compared in the research experiment.

B0  keyword/regex rules (no AI)
B1  end-to-end LLM: programme text + profile -> verdicts
B2  B1 with chain-of-thought
S1  criterion-level LLM judgement (criteria segmented by the extractor, LLM decides each)
S2  neuro-symbolic: LLM extracts criteria into the schema, the rule engine decides;
    the LLM is used only for SEMANTIC criteria (semantic judge)

Fairness (supervisor's point 4): every system gets the same programme text (the same
retrieved eligibility sections by default), the same profile and the same model.
"""
from __future__ import annotations

import re
import time
from datetime import date
from typing import Optional

from ..llm.client import CallMeta, LLMError, chat_json
from ..retrieval import format_sections, retrieve, split_sections
from ..rules.engine import age_on, combine, evaluate, resolve_groups, target_level
from ..schemas import (Criterion, CriterionVerdict, CriterionType, EligibilityResult,
                       GradeScale, Label, Profile, Programme)
from .common import B1Out, LabelOut, build_messages, profile_json
from .criteria import extract_criteria


def programme_context(p: Programme, context: str = "retrieved", k: int = 6) -> str:
    secs = retrieve(p.text, k=k) if context == "retrieved" else split_sections(p.text)
    return format_sections(secs)


def _finish(res: EligibilityResult, metas: list[CallMeta], t0: float) -> EligibilityResult:
    res.latency_s = round(time.perf_counter() - t0, 3)
    costs = [m.cost_usd for m in metas]
    res.cost_usd = None if any(c is None for c in costs) else round(sum(costs), 6)
    return res


# --------------------------------------------------------------------------- B0
def run_b0(prog: Programme, prof: Profile, today: date, context: str = "retrieved", **_) -> EligibilityResult:
    t0 = time.perf_counter()
    text = programme_context(prog, context)
    verdicts: list[CriterionVerdict] = []
    bach = prof.highest()
    m = re.search(r"(?:CGPA|GPA)[^0-9]{0,15}([0-4]\.\d+)", text, re.I)
    if m:
        ok = bool(bach and bach.grade_scale == GradeScale.CGPA_4 and bach.grade_value is not None
                  and bach.grade_value >= float(m[1]))
        verdicts.append(CriterionVerdict(type=CriterionType.MIN_GRADE, reason=f"regex CGPA {m[1]}",
                                         label=Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE))
    m = re.search(r"IELTS[^0-9]{0,25}(\d(?:\.\d)?)", text, re.I)
    if m:
        ok = any(t.test.upper() == "IELTS" and t.overall >= float(m[1]) for t in prof.english_tests)
        verdicts.append(CriterionVerdict(type=CriterionType.ENGLISH_TEST, reason=f"regex IELTS {m[1]}",
                                         label=Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE))
    m = re.search(r"(?:under|below|younger than|not (?:be )?(?:older|more) than|maximum age(?: of)?|age limit(?: of| is)?)\s*(\d{2})", text, re.I)
    if m and prof.date_of_birth:
        ok = age_on(prof.date_of_birth, today) <= int(m[1])
        verdicts.append(CriterionVerdict(type=CriterionType.AGE_LIMIT, reason=f"regex age {m[1]}",
                                         label=Label.ELIGIBLE if ok else Label.NOT_ELIGIBLE))
    m = re.search(r"(\d{2})\s*years of (?:education|schooling)", text, re.I)
    if m:
        yrs = sum((d.duration_years or 0) for d in prof.degrees if d.level.value in ("bachelor", "master")) + 12
        verdicts.append(CriterionVerdict(type=CriterionType.YEARS_OF_EDUCATION, reason=f"regex {m[1]} years",
                                         label=Label.ELIGIBLE if yrs >= int(m[1]) else Label.NOT_ELIGIBLE))
    res = EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id, system="B0",
                            overall=combine(verdicts), criteria=verdicts)
    return _finish(res, [], t0)


# --------------------------------------------------------------------------- B1 / B2
def run_b1(prog: Programme, prof: Profile, model: str, today: date, cot: bool = False,
           context: str = "retrieved", temperature: float = 0.0, seed: Optional[int] = None,
           use_cache: bool = True, run_tag: str = "", **_) -> EligibilityResult:
    t0 = time.perf_counter()
    msgs = build_messages(
        "b1_end_to_end", today=today.isoformat(), programme_name=prog.name,
        programme_text=programme_context(prog, context), profile_json=profile_json(prof),
        cot="First reason step by step in \"reasoning\", checking every requirement, then give verdicts." if cot else "",
        cot_key='"reasoning": "step-by-step reasoning", ' if cot else "")
    name = "B2" if cot else "B1"
    try:
        out, meta = chat_json(msgs, B1Out, component=name.lower(), model=model, temperature=temperature,
                              seed=seed, use_cache=use_cache, run_tag=run_tag)
    except LLMError as e:
        return EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id, system=name,
                                 overall=Label.INSUFFICIENT, error=str(e)[:200])
    verdicts = [CriterionVerdict(type=c.type, label=c.label, reason=c.reason) for c in out.criteria
                if c.label != Label.MANUAL]
    res = EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id, system=name,
                            overall=out.overall if out.overall != Label.MANUAL else Label.INSUFFICIENT,
                            criteria=verdicts)
    return _finish(res, [meta], t0)


# --------------------------------------------------------------------------- semantic judge (used by S2)
def make_judge(model: str, today: date, temperature: float, seed, use_cache: bool, run_tag: str, metas: list):
    def judge(c: Criterion, p: Profile):
        msgs = build_messages("semantic_judge", requirement=c.text, fields=", ".join(c.fields) or "not listed",
                              quote=c.source_quote or "", profile_json=profile_json(p))
        try:
            out, meta = chat_json(msgs, LabelOut, component="semantic_judge", model=model,
                                  temperature=temperature, seed=seed, use_cache=use_cache, run_tag=run_tag)
        except LLMError as e:
            return Label.INSUFFICIENT, f"judge failed: {e}"[:200]
        metas.append(meta)
        lab = out.label if out.label != Label.MANUAL else Label.INSUFFICIENT
        return lab, out.reason
    return judge


# --------------------------------------------------------------------------- S2
def run_s2(prog: Programme, prof: Profile, model: str, today: date, context: str = "retrieved",
           criteria: Optional[list[Criterion]] = None, temperature: float = 0.0, seed: Optional[int] = None,
           use_cache: bool = True, run_tag: str = "", system_name: str = "S2", **_) -> EligibilityResult:
    """criteria=None -> extract with the LLM; criteria given -> oracle run on gold criteria."""
    t0 = time.perf_counter()
    metas: list[CallMeta] = []
    if criteria is None:
        try:
            criteria, meta = extract_criteria(prog, model, context=context, use_cache=use_cache,
                                              run_tag=run_tag)
            metas.append(meta)
        except LLMError as e:
            return EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id,
                                     system=system_name, overall=Label.INSUFFICIENT, error=str(e)[:200])
    judge = make_judge(model, today, temperature, seed, use_cache, run_tag, metas)
    res = evaluate(prog.programme_id, criteria, prof, semantic_judge=judge, today=today, system=system_name)
    return _finish(res, metas, t0)


# --------------------------------------------------------------------------- S1
def run_s1(prog: Programme, prof: Profile, model: str, today: date, context: str = "retrieved",
           temperature: float = 0.0, seed: Optional[int] = None, use_cache: bool = True,
           run_tag: str = "", **_) -> EligibilityResult:
    t0 = time.perf_counter()
    metas: list[CallMeta] = []
    try:
        criteria, meta = extract_criteria(prog, model, context=context, use_cache=use_cache, run_tag=run_tag)
        metas.append(meta)
    except LLMError as e:
        return EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id, system="S1",
                                 overall=Label.INSUFFICIENT, error=str(e)[:200])
    # same deterministic preprocessing as S2, so S1 and S2 differ only in who judges each criterion
    target = target_level(prof)
    criteria = [c for c in criteria if c.type != CriterionType.DEADLINE and (c.track is None or c.track == target)]
    verdicts = []
    for c in criteria:
        if c.handling.value == "manual_check" or c.type in (CriterionType.DOCUMENT, CriterionType.ADMISSION):
            verdicts.append(CriterionVerdict(criterion_id=c.criterion_id, type=c.type, label=Label.MANUAL,
                                             reason="manual check"))
            continue
        msgs = build_messages("s1_criterion", today=today.isoformat(), type=c.type.value, requirement=c.text,
                              quote=c.source_quote or "", profile_json=profile_json(prof))
        try:
            out, m = chat_json(msgs, LabelOut, component="s1_criterion", model=model, temperature=temperature,
                               seed=seed, use_cache=use_cache, run_tag=run_tag)
            metas.append(m)
            lab = out.label if out.label != Label.MANUAL else Label.INSUFFICIENT
            verdicts.append(CriterionVerdict(criterion_id=c.criterion_id, type=c.type, label=lab,
                                             reason=out.reason, citation=c.source_quote))
        except LLMError as e:
            verdicts.append(CriterionVerdict(criterion_id=c.criterion_id, type=c.type, label=Label.INSUFFICIENT,
                                             reason=f"error: {e}"[:200]))
    resolve_groups(criteria, verdicts)
    res = EligibilityResult(programme_id=prog.programme_id, profile_id=prof.profile_id, system="S1",
                            overall=combine(verdicts), criteria=verdicts)
    return _finish(res, metas, t0)


SYSTEMS = {
    "B0": run_b0,
    "B1": run_b1,
    "B2": lambda *a, **k: run_b1(*a, cot=True, **k),
    "S1": run_s1,
    "S2": run_s2,
}
