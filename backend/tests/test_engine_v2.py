"""Engine v2: track-specific criteria, alternatives, conditional verdicts, documents, to-do list."""
from datetime import date

from scholarfit.rules.engine import evaluate, missing_requirements, target_level
from scholarfit.schemas import (Criterion, CriterionType as T, Degree, DegreeLevel as L, EnglishTest,
                                GradeScale, Label, Profile)


def bachelor_holder(**kw):
    base = dict(profile_id="p", date_of_birth=date(2001, 1, 1), nationality="Pakistan",
                degrees=[Degree(level=L.INTERMEDIATE, duration_years=2, completed=True),
                         Degree(level=L.BACHELOR, field="Computer Science", duration_years=4, completed=True,
                                grade_value=3.4, grade_scale=GradeScale.CGPA_4, grade_scale_max=4.0)],
                english_tests=[], english_medium_instruction=True, work_experience_months=0)
    base.update(kw)
    return Profile(**base)


def test_target_level_defaults_to_next_degree():
    assert target_level(bachelor_holder()) == L.MASTER


def test_track_specific_rule_only_applies_to_its_track():   # MEXT: 16 years (master's), 18 years (doctoral)
    crits = [Criterion(criterion_id="m", type=T.YEARS_OF_EDUCATION, min_years=16, track=L.MASTER),
             Criterion(criterion_id="d", type=T.YEARS_OF_EDUCATION, min_years=18, track=L.PHD)]
    res = evaluate("mext", crits, bachelor_holder())
    assert [v.criterion_id for v in res.criteria] == ["m"]
    assert res.overall == Label.ELIGIBLE


def test_any_of_group_met_by_one_alternative():   # IELTS 6.5 or an English-medium degree
    crits = [Criterion(criterion_id="ielts", type=T.ENGLISH_TEST, english_min_scores={"IELTS": 6.5}, any_of="eng"),
             Criterion(criterion_id="emi", type=T.ENGLISH_TEST, english_min_scores={"IELTS": 99},
                       english_waiver_medium_of_instruction=True, any_of="eng")]
    res = evaluate("x", crits, bachelor_holder())
    assert res.overall == Label.ELIGIBLE
    assert all(v.label == Label.ELIGIBLE for v in res.criteria)


def test_any_of_group_fails_only_when_all_fail():
    crits = [Criterion(criterion_id="a", type=T.MIN_CREDITS, min_ects=300, any_of="g"),
             Criterion(criterion_id="b", type=T.YEARS_OF_EDUCATION, min_years=18, any_of="g")]
    assert evaluate("x", crits, bachelor_holder()).overall == Label.NOT_ELIGIBLE


def test_final_year_student_is_conditional():
    p = bachelor_holder(degrees=[Degree(level=L.INTERMEDIATE, duration_years=2, completed=True),
                                 Degree(level=L.BACHELOR, duration_years=4, completed=False,
                                        expected_completion=date(2027, 6, 30))])
    c = Criterion(type=T.DEGREE_LEVEL, required_level=L.BACHELOR, final_year_allowed=True)
    assert evaluate("x", [c], p).overall == Label.CONDITIONAL


def test_stated_condition_makes_a_met_criterion_conditional():
    c = Criterion(type=T.NATIONALITY, nationalities_allowed=["Pakistan"], condition="must not hold dual nationality")
    assert evaluate("x", [c], bachelor_holder()).overall == Label.CONDITIONAL


def test_documents_and_admission_are_listed_not_scored():
    crits = [Criterion(criterion_id="n", type=T.NATIONALITY, nationalities_allowed=["Pakistan"]),
             Criterion(criterion_id="t", type=T.DOCUMENT, text="HEC-attested transcripts"),
             Criterion(criterion_id="a", type=T.ADMISSION, text="admission to the host university")]
    res = evaluate("x", crits, bachelor_holder())
    assert res.overall == Label.ELIGIBLE
    todo = missing_requirements(res, crits)
    assert [t["kind"] for t in todo] == ["document", "manual"]


def test_todo_list_orders_unmet_first():
    crits = [Criterion(criterion_id="w", type=T.WORK_EXPERIENCE, min_work_months=24),
             Criterion(criterion_id="g", type=T.AGE_LIMIT, max_age=35),            # no reference date -> undecided
             Criterion(criterion_id="d", type=T.DOCUMENT, text="two recommendation letters")]
    res = evaluate("x", crits, bachelor_holder())
    kinds = [t["kind"] for t in missing_requirements(res, crits)]
    assert kinds == ["not_met", "missing_info", "document"]
