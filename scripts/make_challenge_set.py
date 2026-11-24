"""Build the ScholarElig challenge set: hard profile-programme pairs for a fresh test set.

  python scripts/make_challenge_set.py --n 60 --seed 11

For each programme that has gold criteria (data/labels/criteria_gold.jsonl), the script first
builds a profile that satisfies every stated requirement, then changes ONE thing to create a hard
case: a grade just above or below the threshold, a missing minimum passing grade, an age one day
over the limit, a missing date of birth, one IELTS band too low, no test but an English-medium
certificate, a 2+2-year degree path, a final-year student, the wrong degree level for a track,
work experience just short, a different nationality, or an expired deadline.

The profiles are generated from the criteria FIELDS only; the rule engine is never run, so the set
is not biased towards the system under test. Gold labels are made by two people afterwards, exactly
as for the main set. The scenario of each pair is written to challenge_meta.csv, which annotators
must NOT open before labelling.

Writes:
  data/profiles/challenge/chNNN.json (+ .pdf / .docx CV)
  data/labels/challenge_pairs.csv, challenge_annotatorA.csv, challenge_annotatorB.csv
  data/labels/challenge_meta.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from scholarfit.schemas import (Criterion, CriterionType, Degree, DegreeLevel, EnglishTest,  # noqa: E402
                                GradeRule, GradeScale, Profile)
import make_synthetic_cvs  # noqa: E402
from make_synthetic_cvs import FIRST, LAST, UNIS, COLLEGES, render_docx, render_pdf  # noqa: E402

TYPES = ["min_grade", "years_of_education", "min_credits", "degree_level", "degree_field", "age_limit",
         "nationality", "english_test", "work_experience", "other"]
TODAY = date(2026, 11, 22)


# --------------------------------------------------------------------------- helpers
def by_type(crits: list[Criterion], t: CriterionType) -> list[Criterion]:
    return [c for c in crits if c.type == t]


def ref_date(crits: list[Criterion], snapshot: date | None) -> date:
    for c in by_type(crits, CriterionType.AGE_LIMIT):
        if c.age_reference_date:
            return c.age_reference_date
    for c in by_type(crits, CriterionType.DEADLINE):
        if c.deadline:
            return c.deadline
    return snapshot or TODAY


def cgpa_for(c: Criterion, margin: float) -> float | None:
    """CGPA (4.0 scale, minimum pass 2.0) that sits `margin` above (+) or below (-) the threshold."""
    if c.grade_rule == GradeRule.MODIFIED_BAVARIAN and c.grade_min_value:
        # German grade G = 1 + 3 (4 - N) / (4 - 2); G <= g_req  <=>  N >= 4 - 2 (g_req - 1) / 3
        n = 4 - 2 * (c.grade_min_value - 1) / 3
    elif c.grade_rule in (GradeRule.SAME_SCALE, None) and c.grade_min_value and (c.grade_scale in (GradeScale.CGPA_4, None)) \
            and c.grade_min_value <= 4.0:
        n = c.grade_min_value
    elif c.grade_rule == GradeRule.PROGRAMME_TABLE:
        t = next((t for t in c.thresholds if t.scale == GradeScale.CGPA_4), None)
        if not t:
            return None
        n = t.min_value
    else:
        return None
    v = math.ceil(n * 100) / 100 + margin if margin >= 0 else math.floor(n * 100) / 100 + margin
    return round(min(3.98, max(2.05, v)), 2)


def pct_threshold(c: Criterion) -> float | None:
    """A minimum stated as a percentage (e.g. 'at least 70% overall')."""
    if c.grade_rule == GradeRule.MODIFIED_BAVARIAN:
        return None
    v = c.grade_min_value
    if v and (c.grade_scale == GradeScale.PERCENTAGE or c.grade_rule == GradeRule.PERCENTAGE_THRESHOLD or 4 < v <= 100):
        return v
    return None


def set_pct(p: Profile, value: float):
    for d in p.degrees:
        if d.level in (DegreeLevel.BACHELOR, DegreeLevel.MASTER):
            d.grade_value, d.grade_scale, d.grade_scale_max, d.grade_scale_min_pass = value, GradeScale.PERCENTAGE, 100, 50


def base_profile(crits: list[Criterion], ref: date, rng: random.Random) -> Profile:
    """A profile that satisfies every stated requirement of the programme."""
    field = next((c.fields[0] for c in by_type(crits, CriterionType.DEGREE_FIELD) if c.fields), "Computer Science")
    need_master = any(c.required_level in (DegreeLevel.MASTER, DegreeLevel.PHD) for c in by_type(crits, CriterionType.DEGREE_LEVEL))
    need_years = max([c.min_years or 0 for c in by_type(crits, CriterionType.YEARS_OF_EDUCATION)] + [0])
    cg = 3.6
    for c in by_type(crits, CriterionType.MIN_GRADE):
        v = cgpa_for(c, 0.25)
        if v:
            cg = max(cg, v)
    degrees = [Degree(level=DegreeLevel.INTERMEDIATE, title="F.Sc. Pre-Engineering", duration_years=2, completed=True,
                      grade_value=round(rng.uniform(75, 88), 1), grade_scale=GradeScale.PERCENTAGE, grade_scale_max=100),
               Degree(level=DegreeLevel.BACHELOR, title=f"BS {field}", field=field, institution=rng.choice(UNIS),
                      country="Pakistan", duration_years=4, completed=True, grade_value=cg,
                      grade_scale=GradeScale.CGPA_4, grade_scale_max=4.0, grade_scale_min_pass=2.0)]
    if need_master or need_years > 16:
        degrees.append(Degree(level=DegreeLevel.MASTER, title=f"MS {field}", field=field, institution=rng.choice(UNIS),
                              country="Pakistan", duration_years=2, completed=True, grade_value=min(3.95, cg + 0.1),
                              grade_scale=GradeScale.CGPA_4, grade_scale_max=4.0, grade_scale_min_pass=2.0))
    age = 26
    for c in by_type(crits, CriterionType.AGE_LIMIT):
        if c.max_age:
            age = min(age, c.max_age - 3)
    dob = date(ref.year - age, rng.randint(1, 12), rng.randint(1, 28))
    for c in by_type(crits, CriterionType.AGE_LIMIT):
        if c.born_on_or_after and dob < c.born_on_or_after:
            dob = c.born_on_or_after + timedelta(days=400)
    tests = []
    ec = next(iter(by_type(crits, CriterionType.ENGLISH_TEST)), None)
    test = "IELTS"
    overall, band = 7.0, 6.5
    if ec and ec.english_min_scores:
        test = "IELTS" if "IELTS" in ec.english_min_scores else next(iter(ec.english_min_scores))
        overall = max(overall, ec.english_min_scores[test] + (0.5 if test == "IELTS" else 8))
    if ec and ec.english_min_band.get(test):
        band = max(band, ec.english_min_band[test] + 0.5)
    tests.append(EnglishTest(test=test, overall=overall, min_band=band if test == "IELTS" else None))
    work = max([c.min_work_months or 0 for c in by_type(crits, CriterionType.WORK_EXPERIENCE)] + [0]) + 12
    nat = "Pakistan"
    for c in by_type(crits, CriterionType.NATIONALITY):
        if c.nationalities_allowed and not any("pakistan" in n.lower() for n in c.nationalities_allowed):
            nat = c.nationalities_allowed[0]
    prof = Profile(date_of_birth=dob, nationality=nat, degrees=degrees, english_tests=tests,
                   english_medium_instruction=None, work_experience_months=work, interests=["machine learning"])
    pct = [pct_threshold(c) for c in by_type(crits, CriterionType.MIN_GRADE) if pct_threshold(c)]
    if pct:                                  # the call states a percentage: give the grade on that scale
        set_pct(prof, min(95.0, max(pct) + 8))
    return prof


def shift_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:          # 29 February
        return d.replace(year=d.year - years, day=28)


def bachelor(p: Profile) -> Degree:
    return next(d for d in p.degrees if d.level == DegreeLevel.BACHELOR)


# --------------------------------------------------------------------------- scenarios
# each returns a changed profile (or None if it does not apply) and the class the change is aimed at
def s_clean(p, crits, ref, prog):
    return p, "E", "meets every stated requirement"


def s_grade_above(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.MIN_GRADE) if cgpa_for(c, 0.01)), None)
    if not c:
        return None
    for d in p.degrees:
        if d.level in (DegreeLevel.BACHELOR, DegreeLevel.MASTER):
            d.grade_value = cgpa_for(c, 0.01)
    return p, "E", f"grade just above the threshold ({c.grade_rule.value if c.grade_rule else 'same scale'})"


def s_grade_below(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.MIN_GRADE) if cgpa_for(c, -0.02)), None)
    if not c:
        return None
    for d in p.degrees:
        if d.level in (DegreeLevel.BACHELOR, DegreeLevel.MASTER):
            d.grade_value = cgpa_for(c, -0.02)
    return p, "NE", "grade just below the threshold"


def s_pct_above(p, crits, ref, prog):
    t = next((pct_threshold(c) for c in by_type(crits, CriterionType.MIN_GRADE) if pct_threshold(c)), None)
    if not t:
        return None
    set_pct(p, t + 0.5)
    return p, "E", "percentage grade just above the stated minimum"


def s_pct_below(p, crits, ref, prog):
    t = next((pct_threshold(c) for c in by_type(crits, CriterionType.MIN_GRADE) if pct_threshold(c)), None)
    if not t:
        return None
    set_pct(p, t - 0.5)
    return p, "NE", "percentage grade just below the stated minimum"


def s_no_min_pass(p, crits, ref, prog):
    if not any(c.grade_rule == GradeRule.MODIFIED_BAVARIAN for c in by_type(crits, CriterionType.MIN_GRADE)):
        return None
    for d in p.degrees:
        d.grade_scale_min_pass = None
    return p, "II", "modified Bavarian rule but the CV does not state the minimum passing grade"


def s_percentage_scale(p, crits, ref, prog):
    if not by_type(crits, CriterionType.MIN_GRADE):
        return None
    b = bachelor(p)
    b.grade_value, b.grade_scale, b.grade_scale_max, b.grade_scale_min_pass = 71.5, GradeScale.PERCENTAGE, 100, 40
    p.degrees = [d for d in p.degrees if d.level != DegreeLevel.MASTER] if not any(
        c.required_level == DegreeLevel.MASTER for c in by_type(crits, CriterionType.DEGREE_LEVEL)) else p.degrees
    return p, "II", "grade on a percentage scale; the programme may give no rule for it"


def s_age_over(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.AGE_LIMIT) if c.max_age or c.born_on_or_after), None)
    if not c:
        return None
    if c.born_on_or_after:
        p.date_of_birth = c.born_on_or_after - timedelta(days=1)
    else:   # turns max_age + 1 one day before the reference date
        p.date_of_birth = shift_years(ref, c.max_age + 1) - timedelta(days=1)
    return p, "NE", "one day over the age limit on the reference date"


def s_age_edge_ok(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.AGE_LIMIT) if c.max_age or c.born_on_or_after), None)
    if not c:
        return None
    if c.born_on_or_after:
        p.date_of_birth = c.born_on_or_after
    else:   # exactly max_age on the reference date, birthday the day after
        p.date_of_birth = shift_years(ref, c.max_age + 1) + timedelta(days=1)
    return p, "E", "exactly at the age limit on the reference date"


def s_no_dob(p, crits, ref, prog):
    if not by_type(crits, CriterionType.AGE_LIMIT):
        return None
    p.date_of_birth = None
    return p, "II", "age limit but no date of birth on the CV"


def s_no_grade(p, crits, ref, prog):
    if not by_type(crits, CriterionType.MIN_GRADE):
        return None
    for d in p.degrees:
        if d.level in (DegreeLevel.BACHELOR, DegreeLevel.MASTER):
            d.grade_value = d.grade_scale = d.grade_scale_max = d.grade_scale_min_pass = None
    return p, "II", "grade requirement but the CV gives no grade"


def s_no_work_info(p, crits, ref, prog):
    if not any(c.min_work_months for c in by_type(crits, CriterionType.WORK_EXPERIENCE)):
        return None
    p.work_experience_months = None
    return p, "II", "work-experience requirement but the CV does not state any dates"


def s_no_nationality(p, crits, ref, prog):
    if not by_type(crits, CriterionType.NATIONALITY):
        return None
    p.nationality = None
    return p, "II", "nationality requirement but the CV does not state nationality"


def s_band_low(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.ENGLISH_TEST) if c.english_min_band.get("IELTS")), None)
    if not c:
        return None
    p.english_tests = [EnglishTest(test="IELTS", overall=max(7.0, c.english_min_scores.get("IELTS", 6.5) + 0.5),
                                   min_band=c.english_min_band["IELTS"] - 0.5)]
    return p, "NE", "IELTS overall meets the requirement but one band is too low"


def s_emi_waiver(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.ENGLISH_TEST) if c.english_waiver_medium_of_instruction), None)
    if not c:
        return None
    p.english_tests, p.english_medium_instruction = [], True
    return p, "E", "no English test, English-medium certificate, programme states a waiver"


def s_no_test(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.ENGLISH_TEST)
              if c.english_min_scores and not c.english_waiver_medium_of_instruction), None)
    if not c:
        return None
    p.english_tests, p.english_medium_instruction = [], True
    return p, "NE", "no English test; English-medium certificate but no waiver stated"


def s_two_plus_two(p, crits, ref, prog):
    if not (by_type(crits, CriterionType.YEARS_OF_EDUCATION) or by_type(crits, CriterionType.MIN_CREDITS)):
        return None
    field = bachelor(p).field
    p.degrees = [p.degrees[0],
                 Degree(level=DegreeLevel.BACHELOR, title="B.Sc. (Physics, Mathematics)", field="Physics and Mathematics",
                        country="Pakistan", duration_years=2, completed=True, grade_value=72.0,
                        grade_scale=GradeScale.PERCENTAGE, grade_scale_max=100, grade_scale_min_pass=33),
                 Degree(level=DegreeLevel.MASTER, title=f"M.Sc. {field}", field=field, country="Pakistan",
                        duration_years=2, completed=True, grade_value=3.5, grade_scale=GradeScale.CGPA_4,
                        grade_scale_max=4.0, grade_scale_min_pass=2.0)]
    return p, "E", "alternative qualification: 2-year B.Sc. plus 2-year M.Sc. (16 years)"


def s_two_year_only(p, crits, ref, prog):
    if not (by_type(crits, CriterionType.YEARS_OF_EDUCATION) or by_type(crits, CriterionType.MIN_CREDITS)):
        return None
    p.degrees = [p.degrees[0],
                 Degree(level=DegreeLevel.BACHELOR, title="B.Sc. (Physics, Mathematics)", field="Physics and Mathematics",
                        country="Pakistan", duration_years=2, completed=True, grade_value=78.0,
                        grade_scale=GradeScale.PERCENTAGE, grade_scale_max=100, grade_scale_min_pass=33)]
    return p, "NE", "only a 2-year B.Sc. (14 years of education)"


def s_alevels(p, crits, ref, prog):
    p.degrees[0] = Degree(level=DegreeLevel.INTERMEDIATE, title="A-Levels", duration_years=2, completed=True)
    return p, "E", "A-levels instead of F.Sc."


def s_final_year(p, crits, ref, prog):
    if not by_type(crits, CriterionType.DEGREE_LEVEL):
        return None
    p.degrees = [d for d in p.degrees if d.level != DegreeLevel.MASTER]
    b = bachelor(p)
    b.completed, b.expected_completion = False, date(ref.year if ref.month > 6 else ref.year, 6, 30)
    allowed = any(c.final_year_allowed for c in by_type(crits, CriterionType.DEGREE_LEVEL))
    return p, "E" if allowed else "NE", "final-year student, graduation expected before the programme starts"


def s_wrong_level(p, crits, ref, prog):
    if not any(c.required_level in (DegreeLevel.MASTER, DegreeLevel.PHD) for c in by_type(crits, CriterionType.DEGREE_LEVEL)):
        if not any((c.min_years or 0) > 16 for c in by_type(crits, CriterionType.YEARS_OF_EDUCATION)):
            return None
    p.degrees = [d for d in p.degrees if d.level != DegreeLevel.MASTER]
    return p, "NE", "bachelor's degree only; a track or requirement asks for a master's (check track conditions)"


def s_work_short(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.WORK_EXPERIENCE) if c.min_work_months), None)
    if not c:
        return None
    p.work_experience_months = c.min_work_months - 1
    return p, "NE", "work experience one month short"


def s_other_nationality(p, crits, ref, prog):
    c = next((c for c in by_type(crits, CriterionType.NATIONALITY) if c.nationalities_allowed or c.nationalities_excluded), None)
    if not c:
        return None
    p.nationality = "India" if c.nationalities_allowed else (c.nationalities_excluded[0] if c.nationalities_excluded else "India")
    return p, "NE", "nationality outside the eligible list"


def s_expired(p, crits, ref, prog):
    if not any(c.deadline and c.deadline < TODAY for c in by_type(crits, CriterionType.DEADLINE)):
        return None
    return p, "E", "meets every requirement but the deadline has passed (label ignores deadlines)"


SCENARIOS = [s_clean, s_grade_above, s_grade_below, s_pct_above, s_pct_below, s_no_min_pass, s_percentage_scale, s_age_over, s_age_edge_ok,
             s_no_dob, s_no_grade, s_no_work_info, s_no_nationality, s_band_low, s_emi_waiver, s_no_test, s_two_plus_two, s_two_year_only, s_alevels,
             s_final_year, s_wrong_level, s_work_short, s_other_nationality, s_expired]


# --------------------------------------------------------------------------- CV rendering
def cv_doc(p: Profile, rng: random.Random) -> dict:
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    edu = []
    for d in p.degrees:
        if d.level == DegreeLevel.INTERMEDIATE:
            detail = f"Marks: {d.grade_value}%" if d.grade_value else "Grades: A A B"
            edu.append((d.title, rng.choice(COLLEGES), "2015 - 2017", detail))
            continue
        if d.grade_value is None:
            detail = "Degree completed"
        elif d.grade_scale == GradeScale.CGPA_4:
            detail = f"CGPA: {d.grade_value:.2f}/4.00"
            if d.grade_scale_min_pass:
                detail += f"; minimum passing CGPA {d.grade_scale_min_pass:.2f}"
        else:
            detail = f"Percentage: {d.grade_value}%" + (f"; pass marks {d.grade_scale_min_pass:.0f}%" if d.grade_scale_min_pass else "")
        when = f"{d.duration_years:g}-year programme" + (
            f", expected {d.expected_completion.strftime('%B %Y')}" if d.expected_completion and not d.completed else "")
        edu.append((d.title, d.institution or rng.choice(UNIS), when, detail))
    eng = None
    if p.english_tests:
        t = p.english_tests[0]
        eng = f"{t.test.replace('_', ' ')}: overall {t.overall}" + (f" (lowest band {t.min_band})" if t.min_band else "")
    months = p.work_experience_months
    jobs = [("Software Engineer", "Systems Ltd", "Jan 2024", "", months)] if months else []
    if months is None:      # job listed without dates, so the duration cannot be worked out
        jobs = [("Software Engineer", "Systems Ltd", "", "", "dates not given")]
    return {"name": name, "email": name.lower().replace(" ", ".") + "@example.com",
            "phone": f"+92 3{rng.randint(0, 4)}{rng.randint(0, 9)} {rng.randint(1000000, 9999999)}",
            "dob": p.date_of_birth.strftime("%d %B %Y") if p.date_of_birth else None,
            "nationality": {"Pakistan": "Pakistani", "India": "Indian"}.get(p.nationality, p.nationality) or "",
            "education": edu[::-1], "english": eng,
            "emi": "Medium of instruction certificate: bachelor's degree taught entirely in English"
            if p.english_medium_instruction else None,
            "jobs": jobs, "interests": p.interests, "skills": ["Python", "SQL", "PyTorch", "Git"]}


def text_blocks(doc):
    """Like make_synthetic_cvs.text_blocks, but leaves out fields the scenario removed."""
    personal = [f"Email: {doc['email']}", f"Phone: {doc['phone']}"]
    if doc["dob"]:
        personal.append(f"Date of Birth: {doc['dob']}")
    if doc["nationality"]:
        personal.append(f"Nationality: {doc['nationality']}")
    blocks = [("Personal Information", personal)]
    edu = []
    for title, inst, when, detail in doc["education"]:
        edu += [f"{title} - {inst} ({when})", f"    {detail}"]
    if doc["emi"]:
        edu.append(doc["emi"])
    blocks.append(("Education", edu))
    if doc["english"]:
        blocks.append(("English Language Proficiency", [doc["english"]]))
    exp = []
    for j, c, _s, _e, n in doc["jobs"]:
        exp.append(f"{j} at {c}" + (f" ({n} months, full time)" if isinstance(n, int) else ""))
    blocks.append(("Experience", exp or ["No work experience yet."]))
    blocks.append(("Research Interests", [", ".join(doc["interests"])]))
    blocks.append(("Skills", [", ".join(doc["skills"])]))
    return blocks


make_synthetic_cvs.text_blocks = text_blocks     # the renderers look this name up at call time


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--max-per-programme", type=int, default=6)
    ap.add_argument("--aim", default="", help="only scenarios aimed at these classes, e.g. E or E,NE")
    ap.add_argument("--programmes", default="", help="comma-separated programme ids to use")
    ap.add_argument("--start", type=int, default=1, help="number of the first new pair (use 61 to add to 60)")
    ap.add_argument("--append", action="store_true", help="add to the existing challenge files")
    args = ap.parse_args()
    aim = set(filter(None, args.aim.split(",")))
    only = set(filter(None, args.programmes.split(",")))
    rng = random.Random(args.seed)

    gold = defaultdict(list)
    for line in (ROOT / "data/labels/criteria_gold.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            gold[d.pop("programme_id")].append(Criterion(**d))
    progs = {json.loads(l)["programme_id"]: json.loads(l)
             for l in (ROOT / "data/programmes/programmes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    split = {r["programme_id"]: r["split"] for r in csv.DictReader((ROOT / "data/labels/pairs.csv").open(encoding="utf-8"))}

    candidates = []
    for pid, crits in gold.items():
        if pid not in progs or (only and pid not in only):
            continue
        snap = progs[pid].get("snapshot_date")
        ref = ref_date(crits, date.fromisoformat(str(snap)) if snap else None)
        for fn in SCENARIOS:
            base = base_profile(crits, ref, random.Random(hash((pid, fn.__name__, args.seed)) & 0xffffffff))
            out = fn(base, crits, ref, progs[pid])
            if out and (not aim or out[1] in aim):
                candidates.append((pid, fn.__name__[2:], out[1], out[2], out[0]))

    # prefer programmes from the test split; spread over scenarios and programmes; balance aimed-at classes
    rng.shuffle(candidates)
    candidates.sort(key=lambda c: 0 if split.get(c[0], "test") == "test" else 1)
    chosen, per_prog, per_scen, per_cls = [], Counter(), Counter(), Counter()
    target_cls = {"E": args.n // 3, "NE": args.n // 3, "II": args.n - 2 * (args.n // 3)}
    if aim:
        target_cls = {k: (args.n if k in aim else 0) for k in target_cls}
    for rnd in range(4):
        for c in candidates:
            if len(chosen) >= args.n or c in chosen:
                continue
            pid, scen, cls = c[0], c[1], c[2]
            if per_prog[pid] >= args.max_per_programme or per_scen[scen] > rnd * 2 + 1:
                continue
            if rnd < 3 and per_cls[cls] >= target_cls[cls]:
                continue
            chosen.append(c)
            per_prog[pid] += 1
            per_scen[scen] += 1
            per_cls[cls] += 1

    prof_dir = ROOT / "data/profiles/challenge"
    prof_dir.mkdir(parents=True, exist_ok=True)
    lab = ROOT / "data/labels"
    header = ["pair_id", "split", "profile_id", "programme_id", "family", "annotator"] + [f"label_{t}" for t in TYPES] \
        + ["overall", "evidence", "notes"]
    rows, meta = [], []
    for i, (pid, scen, cls, note, prof) in enumerate(chosen, args.start):
        prof.profile_id = f"ch{i:03d}"
        (prof_dir / f"{prof.profile_id}.json").write_text(prof.model_dump_json(indent=1, exclude_none=True), encoding="utf-8")
        doc = cv_doc(prof, rng)
        if i % 4 == 0:
            render_docx(doc, prof_dir / f"{prof.profile_id}.docx")
        else:
            render_pdf(doc, prof_dir / f"{prof.profile_id}.pdf", layout=i % 3)
        pair_id = f"chal{i:03d}"
        rows.append([pair_id, "test", prof.profile_id, pid, progs[pid]["family"], ""] + [""] * len(TYPES) + ["", "", ""])
        meta.append([pair_id, pid, split.get(pid, "unknown"), scen, cls, note])
    mode = "a" if args.append else "w"
    names = ("challenge_pairs.csv", "challenge_annotatorA.csv", "challenge_annotatorB.csv")
    if args.append:     # new pairs go to separate files for labelling, and are appended to the master list
        names = ("challenge_pairs.csv", "challenge2_annotatorA.csv", "challenge2_annotatorB.csv")
    for name in names:
        m = "a" if (args.append and name == "challenge_pairs.csv") else "w"
        with (lab / name).open(m, newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if m == "w":
                w.writerow(header)
            w.writerows(rows)
    with (lab / "challenge_meta.csv").open(mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["pair_id", "programme_id", "original_split", "scenario", "aimed_at", "note"])
        w.writerows(meta)
    if args.append:
        with (lab / "challenge2_pairs.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
    print(f"wrote {len(rows)} challenge pairs over {len(per_prog)} programmes")
    print("aimed-at classes (the real gold labels come from the annotators):", dict(per_cls))
    print("scenarios:", dict(per_scen))
    print("from dev-split programmes:", sum(1 for m in meta if m[2] == "dev"))


if __name__ == "__main__":
    main()
