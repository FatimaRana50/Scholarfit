"""App v2: ranking, breakdown, saved programmes and the /api/check response (no API key needed)."""
import json
import os
from datetime import date, timedelta

import pytest

os.environ["SCHOLARFIT_MOCK"] = "1"

from scholarfit import ranking, store  # noqa: E402
from scholarfit.schemas import (Criterion, CriterionType, Degree, DegreeLevel, GradeScale,  # noqa: E402
                                Handling, Profile, Programme)


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "t.db")
    return tmp_path


def profile(**kw):
    base = dict(profile_id="p1", nationality="Pakistan", date_of_birth="2001-03-01",
                degrees=[Degree(level=DegreeLevel.INTERMEDIATE, completed=True),
                         Degree(level=DegreeLevel.BACHELOR, field="Computer Science", duration_years=4, completed=True,
                                grade_value=3.4, grade_scale=GradeScale.CGPA_4, grade_scale_max=4.0)],
                interests=["machine learning", "robotics"])
    base.update(kw)
    return Profile(**base)


# --------------------------------------------------------------------------- ranking
def test_urgency_bands():
    t = date(2026, 11, 27)
    assert ranking.urgency_score(t + timedelta(days=10), t) == 1.0
    assert ranking.urgency_score(t + timedelta(days=60), t) == 0.5
    assert ranking.urgency_score(t + timedelta(days=200), t) == 0.2
    assert ranking.urgency_score(None, t) == 0.0
    assert ranking.urgency_score(t - timedelta(days=1), t) == 0.0


def test_funding_from_sources_yaml():
    assert ranking.funding_score("sh-call") == (1.0, "full")
    assert ranking.funding_score("od-mipt") == (0.6, "partial")
    assert ranking.funding_score("no-such-programme") == (0.5, None)


def test_tfidf_relevance_prefers_matching_field():
    docs = {"cs": "Master in Computer Science and machine learning, robotics, artificial intelligence",
            "law": "Master of Laws in international human rights law and legal studies"}
    ranking._INDEX.update(key=None, index=None)
    p = profile()
    assert ranking.relevance_score(p, "cs", docs) > ranking.relevance_score(p, "law", docs)
    assert 0.0 <= ranking.relevance_score(p, "cs", docs) <= 1.0


def test_sort_key_outdated_last_then_verdict_then_score():
    rows = [
        {"name": "A", "overall": "eligible", "outdated": True, "ranking": {"score": 0.9}},
        {"name": "B", "overall": "insufficient_info", "outdated": False, "ranking": {"score": 0.9}},
        {"name": "C", "overall": "eligible", "outdated": False, "ranking": {"score": 0.2}},
        {"name": "D", "overall": "eligible", "outdated": False, "ranking": {"score": 0.7}},
        {"name": "E", "overall": "conditional", "outdated": False, "ranking": {"score": 0.1}},
    ]
    assert [r["name"] for r in sorted(rows, key=ranking.sort_key)] == ["D", "C", "E", "B", "A"]


# --------------------------------------------------------------------------- saved programmes
def test_saved_lifecycle_and_status_change(tmp_db):
    store.upsert_programme(Programme(programme_id="x", family="daad", name="X"))
    store.save_programme("p1", "x", "insufficient_info", {"name": "X"})
    assert [s["programme_id"] for s in store.list_saved("p1")] == ["x"]
    assert store.update_saved_status("p1", "x", "insufficient_info", {}) is None
    assert store.update_saved_status("p1", "x", "eligible", {}) == {"from": "insufficient_info", "to": "eligible"}
    s = store.list_saved("p1")[0]
    assert (s["prev_overall"], s["last_overall"]) == ("insufficient_info", "eligible") and s["changed_at"]
    assert store.update_saved_status("p2", "x", "eligible", {}) is None      # not saved by this student
    assert store.delete_saved("p1", "x") and store.list_saved("p1") == []


# --------------------------------------------------------------------------- /api/check
def _catalogue(deadline):
    crits = [
        Criterion(criterion_id="x-nat", type=CriterionType.NATIONALITY, nationalities_allowed=["Pakistan"],
                  text="Citizens of Pakistan", source_quote="Open to citizens of Pakistan.", confidence=1.0),
        Criterion(criterion_id="x-eng", type=CriterionType.ENGLISH_TEST, english_min_scores={"IELTS": 6.5},
                  text="IELTS 6.5", source_quote="IELTS 6.5 overall.", confidence=1.0),
        Criterion(criterion_id="x-doc", type=CriterionType.DOCUMENT, text="Two reference letters",
                  source_quote="Two letters of reference.", confidence=1.0),
        Criterion(criterion_id="x-dl", type=CriterionType.DEADLINE, deadline=deadline, text="Deadline",
                  source_quote="Apply by the deadline.", confidence=1.0),
    ]
    store.upsert_programme(Programme(programme_id="x", family="daad", name="X programme", text="computer science"))
    store.save_criteria("x", crits, "test")
    for c in crits:   # documents are saved as needs_review; approve all for the test
        store.review_criterion(c.criterion_id, "t", True)


def test_check_returns_outdated_missing_breakdown_and_ranking(tmp_db, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "CHANGES_FILE", tmp_db / "changes.json")
    (tmp_db / "changes.json").write_text(json.dumps({"changed": [{"programme_id": "x", "new_snapshot": "2026-11-27"}]}))
    _catalogue(date(2020, 1, 1))
    store.save_programme("p1", "x", "eligible", None)
    rows = main.check(main.CheckRequest(profile=profile(), programme_ids=["x"]))
    r = rows[0]
    assert r["outdated"] is True
    assert r["overall"] == "not_eligible"                       # no IELTS in the profile
    kinds = [m["kind"] for m in r["missing"]]
    assert kinds[0] == "not_met" and "document" in kinds
    by_id = {c["criterion_id"]: c for c in r["criteria"]}
    assert by_id["x-nat"]["result"] == "Met" and by_id["x-nat"]["your_profile"] == "Pakistan"
    assert by_id["x-eng"]["result"] == "Not met" and by_id["x-eng"]["citation"] == "IELTS 6.5 overall."
    assert by_id["x-doc"]["result"] == "Document to prepare"
    assert set(r["ranking"]) >= {"score", "relevance", "funding", "urgency"}
    assert r["call_changed"]["programme_id"] == "x"
    assert r["status_change"] == {"from": "eligible", "to": "not_eligible"}
    assert main.history("p1")[0]["programme_id"] == "x"


def test_curator_endpoints_need_the_key(monkeypatch):
    from fastapi import HTTPException
    from app import main
    monkeypatch.setenv("CURATOR_KEY", "secret")
    for bad in (None, "wrong"):
        with pytest.raises(HTTPException) as e:
            main.require_curator(bad)
        assert e.value.status_code == 401
    main.require_curator("secret")             # no error
    monkeypatch.delenv("CURATOR_KEY")
    with pytest.raises(HTTPException) as e:
        main.require_curator("secret")
    assert e.value.status_code == 503
