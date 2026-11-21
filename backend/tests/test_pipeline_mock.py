"""Offline end-to-end checks with fake model responses (no API key needed)."""
import json
import os
from datetime import date
from pathlib import Path

os.environ["SCHOLARFIT_MOCK"] = "1"

from scholarfit.pipelines.systems import SYSTEMS  # noqa: E402
from scholarfit.retrieval import quote_in_text, retrieve  # noqa: E402
from scholarfit.schemas import Label, Profile, Programme  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[2]


def prog():
    return Programme(**json.loads((FIX / "programmes.jsonl").read_text().splitlines()[0]))


def profile():
    return Profile(**json.loads((ROOT / "data/profiles/synthetic/syn001.json").read_text()))


def test_retrieval_finds_eligibility_section():
    secs = retrieve(prog().text, k=2)
    assert any("Eligibility" in s.heading for s in secs)


def test_quote_check():
    p = prog()
    assert quote_in_text("Applicants need a CGPA of at least 3.0 on a 4.0 scale.", p.text)
    assert not quote_in_text("Applicants need a CGPA of 3.5.", p.text)


def test_all_systems_run():
    for name, fn in SYSTEMS.items():
        r = fn(prog(), profile(), model="gemini-flash", today=date(2026, 11, 21), use_cache=False)
        assert r.error is None, (name, r.error)
        assert r.overall in (Label.ELIGIBLE, Label.NOT_ELIGIBLE, Label.INSUFFICIENT)


def test_s2_marks_interview_manual():
    r = SYSTEMS["S2"](prog(), profile(), model="gemini-flash", today=date(2026, 11, 21), use_cache=False)
    assert any(v.label == Label.MANUAL for v in r.criteria)
    assert all(v.citation for v in r.criteria)
