from datetime import date

from scholarfit.rules.engine import age_on, combine, evaluate
from scholarfit.rules.grades import modified_bavarian
from scholarfit.schemas import (Criterion, CriterionType as T, CriterionVerdict, Degree,
                                DegreeLevel as L, EnglishTest, GradeRule, GradeScale,
                                Handling, Label, Profile, ScaleThreshold)


def profile(**kw):
    base = dict(
        profile_id="p1", date_of_birth=date(2003, 5, 10), nationality="Pakistan",
        degrees=[
            Degree(level=L.INTERMEDIATE, duration_years=2, completed=True),
            Degree(level=L.BACHELOR, field="Computer Science", duration_years=4, completed=True,
                   grade_value=3.61, grade_scale=GradeScale.CGPA_4, grade_scale_max=4.0,
                   grade_scale_min_pass=2.0),
        ],
        english_tests=[EnglishTest(test="IELTS", overall=7.0, min_band=6.5)],
        english_medium_instruction=True, work_experience_months=6)
    base.update(kw)
    return Profile(**base)


def run(c, p=None, **kw):
    return evaluate("x", [c], p or profile(), **kw).criteria[0].label


# ---- grade conversion
def test_modified_bavarian_formula():
    assert modified_bavarian(4.0, 4.0, 2.0) == 1.0
    assert modified_bavarian(2.0, 4.0, 2.0) == 4.0
    assert abs(modified_bavarian(3.61, 4.0, 2.0) - 1.585) <= 0.01


def test_bavarian_eligible_and_not():
    c = Criterion(type=T.MIN_GRADE, grade_rule=GradeRule.MODIFIED_BAVARIAN, grade_scale=GradeScale.GERMAN,
                  grade_min_value=2.5)
    assert run(c) == Label.ELIGIBLE
    p = profile()
    p.degrees[1].grade_value = 2.6   # -> German 3.1
    assert run(c, p) == Label.NOT_ELIGIBLE


def test_bavarian_needs_min_pass():
    c = Criterion(type=T.MIN_GRADE, grade_rule=GradeRule.MODIFIED_BAVARIAN, grade_scale=GradeScale.GERMAN,
                  grade_min_value=2.5)
    p = profile()
    p.degrees[1].grade_scale_min_pass = None
    assert run(c, p) == Label.INSUFFICIENT


def test_same_scale_needs_no_rule():
    c = Criterion(type=T.MIN_GRADE, grade_rule=GradeRule.NOT_STATED, grade_scale=GradeScale.CGPA_4,
                  grade_min_value=3.0)
    assert run(c) == Label.ELIGIBLE


def test_different_scale_without_rule_is_insufficient():
    c = Criterion(type=T.MIN_GRADE, grade_rule=GradeRule.NOT_STATED, grade_scale=GradeScale.PERCENTAGE,
                  grade_min_value=70)
    assert run(c) == Label.INSUFFICIENT


def test_programme_table():
    c = Criterion(type=T.MIN_GRADE, grade_rule=GradeRule.PROGRAMME_TABLE, uk_class_min="upper_second",
                  thresholds=[ScaleThreshold(scale=GradeScale.CGPA_4, min_value=3.0),
                              ScaleThreshold(scale=GradeScale.PERCENTAGE, min_value=60)])
    assert run(c) == Label.ELIGIBLE
    p = profile()
    p.degrees[1].grade_value = 2.8
    assert run(c, p) == Label.NOT_ELIGIBLE


# ---- other types
def test_years_of_education_14_vs_16():
    c = Criterion(type=T.YEARS_OF_EDUCATION, min_years=16)
    assert run(c) == Label.ELIGIBLE
    p = profile()
    p.degrees[1].duration_years = 2   # old 2-year BSc -> 14 years
    assert run(c, p) == Label.NOT_ELIGIBLE


def test_years_in_progress():
    c = Criterion(type=T.YEARS_OF_EDUCATION, min_years=16)
    p = profile()
    p.degrees[1].completed = False
    assert run(c, p) == Label.INSUFFICIENT
    c.final_year_allowed = True
    assert run(c, p) == Label.ELIGIBLE


def test_ects():
    assert run(Criterion(type=T.MIN_CREDITS, min_ects=180)) == Label.ELIGIBLE
    assert run(Criterion(type=T.MIN_CREDITS, min_ects=300)) == Label.NOT_ELIGIBLE


def test_age_limit_and_born_after():
    assert age_on(date(2003, 5, 10), date(2027, 5, 9)) == 23
    c = Criterion(type=T.AGE_LIMIT, max_age=23, age_reference_date=date(2027, 5, 10))
    assert run(c) == Label.NOT_ELIGIBLE    # turns 24 that day
    c = Criterion(type=T.AGE_LIMIT, born_on_or_after=date(1992, 4, 2))
    assert run(c) == Label.ELIGIBLE
    assert run(c, profile(date_of_birth=None)) == Label.INSUFFICIENT


def test_age_uses_deadline_when_no_reference():
    crit = [Criterion(type=T.AGE_LIMIT, max_age=22), Criterion(type=T.DEADLINE, deadline=date(2026, 1, 1))]
    r = evaluate("x", crit, profile(), today=date(2025, 12, 1))
    assert r.criteria[0].label == Label.ELIGIBLE
    assert r.deadline_open is True


def test_english_and_waiver():
    c = Criterion(type=T.ENGLISH_TEST, english_min_scores={"IELTS": 6.5}, english_min_band={"IELTS": 6.0})
    assert run(c) == Label.ELIGIBLE
    p = profile(english_tests=[EnglishTest(test="IELTS", overall=6.0)])
    assert run(c, p) == Label.NOT_ELIGIBLE
    c.english_waiver_medium_of_instruction = True
    assert run(c, p) == Label.ELIGIBLE
    p2 = profile(english_tests=[], english_medium_instruction=None)
    assert run(c, p2) == Label.INSUFFICIENT


def test_nationality():
    assert run(Criterion(type=T.NATIONALITY, nationalities_allowed=["Pakistan", "India"])) == Label.ELIGIBLE
    assert run(Criterion(type=T.NATIONALITY, nationalities_excluded=["pakistani"])) == Label.NOT_ELIGIBLE


def test_degree_level_final_year():
    p = profile()
    p.degrees[1].completed = False
    c = Criterion(type=T.DEGREE_LEVEL, required_level=L.BACHELOR)
    assert run(c, p) == Label.INSUFFICIENT
    c.final_year_allowed = False
    assert run(c, p) == Label.NOT_ELIGIBLE


def test_manual_and_semantic():
    assert run(Criterion(type=T.OTHER, handling=Handling.MANUAL, text="Olympiad round")) == Label.MANUAL
    assert run(Criterion(type=T.DEGREE_FIELD, fields=["Computer Science"])) == Label.INSUFFICIENT
    judge = lambda c, p: (Label.ELIGIBLE, "CS matches")
    assert run(Criterion(type=T.DEGREE_FIELD, fields=["Computer Science"]), semantic_judge=judge) == Label.ELIGIBLE


def test_combine_ignores_manual():
    v = lambda l: CriterionVerdict(type=T.OTHER, label=l, reason="")
    assert combine([v(Label.ELIGIBLE), v(Label.MANUAL)]) == Label.ELIGIBLE
    assert combine([v(Label.ELIGIBLE), v(Label.INSUFFICIENT)]) == Label.INSUFFICIENT
    assert combine([v(Label.INSUFFICIENT), v(Label.NOT_ELIGIBLE)]) == Label.NOT_ELIGIBLE
    assert combine([]) == Label.INSUFFICIENT
