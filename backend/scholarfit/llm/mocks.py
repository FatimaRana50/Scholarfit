"""Fake model responses for offline testing ONLY (SCHOLARFIT_MOCK=1).

They let the whole pipeline, the experiment runner and the report run without an API
key, so the code can be checked in CI. Numbers produced in mock mode are meaningless
and must never be reported as results.
"""
from __future__ import annotations

import hashlib
import json
import re

from .client import MOCKS


def _user(msgs):
    return msgs[-1]["content"] if msgs[-1]["role"] == "user" else msgs[1]["content"]


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]


def criteria(msgs):
    text = _user(msgs)
    out = []
    for s in _sentences(text):
        m = re.search(r"CGPA of (?:at least )?([0-4]\.\d+)", s)
        if m:
            out.append({"type": "min_grade", "text": s, "source_quote": s, "grade_min_value": float(m[1]),
                        "grade_scale": "cgpa_4", "grade_rule": "not_stated"})
        m = re.search(r"IELTS (?:score of |overall )?(\d(?:\.\d)?)", s)
        if m:
            out.append({"type": "english_test", "text": s, "source_quote": s,
                        "english_min_scores": {"IELTS": float(m[1])}})
        m = re.search(r"under (\d{2}) years", s)
        if m:
            out.append({"type": "age_limit", "text": s, "source_quote": s, "max_age": int(m[1]) - 1})
        m = re.search(r"(\d{2}) years of education", s)
        if m:
            out.append({"type": "years_of_education", "text": s, "source_quote": s, "min_years": int(m[1])})
        if re.search(r"interview", s, re.I):
            out.append({"type": "other", "handling": "manual_check", "text": s, "source_quote": s})
        if re.search(r"related field|relevant field", s, re.I):
            out.append({"type": "degree_field", "handling": "semantic", "text": s, "source_quote": s,
                        "fields": ["Computer Science"]})
    return json.dumps({"criteria": out})


def b1(msgs):
    h = int(hashlib.md5(_user(msgs).encode()).hexdigest(), 16)
    lab = ["eligible", "not_eligible", "insufficient_info"][h % 3]
    return json.dumps({"reasoning": "mock", "criteria": [{"type": "min_grade", "label": lab, "reason": "mock"}],
                       "overall": lab})


def label(msgs):
    return json.dumps({"label": "eligible", "reason": "mock"})


def cv(msgs):
    from ..pipelines.cv import extract_profile_rules
    txt = _user(msgs).split("<cv>", 1)[-1].split("</cv>", 1)[0]
    return extract_profile_rules(txt).model_dump_json(exclude_none=True)


MOCKS.update({"criteria_extract_retrieved": criteria, "criteria_extract_full": criteria, "b1": b1, "b2": b1,
              "semantic_judge": label, "s1_criterion": label, "cv_extract": cv})
