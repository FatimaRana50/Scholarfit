"""Generate synthetic CVs with known (gold) profiles.

  python scripts/make_synthetic_cvs.py --n 50 --seed 7

Writes data/profiles/synthetic/<id>.json (gold Profile) and <id>.pdf or <id>.docx.
Because each CV is rendered FROM its gold profile, the labels are exact by
construction: no language model is involved in making them. CVs vary on purpose:
4.0 CGPA vs percentage, 4-year BS vs 2+2-year BSc/MSc, A-levels vs FSc, final-year
students, missing date of birth, IELTS with sub-scores, TOEFL, no test, English-medium
certificates, several date formats and three page layouts.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from scholarfit.schemas import Degree, DegreeLevel, EnglishTest, GradeScale, Profile  # noqa: E402

FIRST = ["Ayesha", "Hamza", "Fatima", "Ali", "Zainab", "Usman", "Maryam", "Bilal", "Hira", "Saad", "Iqra",
         "Danish", "Mahnoor", "Taha", "Areeba", "Hassan", "Noor", "Omar", "Rida", "Shayan", "Laiba", "Ahmed"]
LAST = ["Khan", "Malik", "Qureshi", "Butt", "Siddiqui", "Chaudhry", "Sheikh", "Raza", "Abbasi", "Farooq",
        "Iqbal", "Hussain", "Javed", "Mirza", "Shah", "Akhtar"]
UNIS = ["FAST-NUCES Islamabad", "NUST Islamabad", "COMSATS University Islamabad", "UET Lahore",
        "University of the Punjab", "Quaid-i-Azam University", "LUMS", "NED University Karachi",
        "University of Peshawar", "Bahria University"]
COLLEGES = ["Punjab Group of Colleges", "Islamabad Model College for Boys", "Beaconhouse School System",
            "Govt. College Rawalpindi", "Roots International", "Fazaia Inter College"]
BS_FIELDS = [("Computer Science", "BS Computer Science"), ("Software Engineering", "BS Software Engineering"),
             ("Data Science", "BS Data Science"), ("Mathematics", "BS Mathematics"),
             ("Business Administration", "BBA (Hons)"), ("English Literature", "BS English"),
             ("Physics", "BS Physics")]
BE_FIELDS = [("Electrical Engineering", "BE Electrical Engineering"),
             ("Mechanical Engineering", "BE Mechanical Engineering"),
             ("Computer Engineering", "BE Computer Engineering")]
JOBS = ["Software Engineer Intern", "Teaching Assistant", "Junior Data Analyst", "Associate Software Engineer",
        "Research Assistant", "Lab Demonstrator", "Web Developer", "Customer Support Associate"]
COMPANIES = ["Systems Ltd", "Folio3", "Arbisoft", "10Pearls", "NetSol", "a university lab", "a local NGO"]
INTERESTS = ["machine learning", "natural language processing", "computer vision", "cybersecurity",
             "distributed systems", "data engineering", "robotics", "human-computer interaction",
             "renewable energy", "finance", "public policy"]


def fmt_date(d: date, style: int) -> str:
    if style == 0:
        return d.strftime("%d %B %Y")
    if style == 1:
        return d.isoformat()
    return d.strftime("%d/%m/%Y")


def make_profile(i: int, rng: random.Random):
    pid = f"syn{i:03d}"
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    dob = None if rng.random() < 0.1 else date(1989, 1, 1) + timedelta(days=rng.randint(0, 6200))
    nat = "Pakistan" if rng.random() < 0.9 else rng.choice(["India", "Bangladesh", "Nepal"])
    demonym = {"Pakistan": "Pakistani", "India": "Indian", "Bangladesh": "Bangladeshi", "Nepal": "Nepalese"}[nat]
    path = rng.choices(["A", "B", "C", "D"], weights=[55, 15, 15, 15])[0]
    in_progress = path in ("A", "D") and rng.random() < 0.2
    end_year = 2026 if in_progress else rng.randint(2014, 2025)
    degrees, edu_lines = [], []
    min_pass_shown = rng.random() < 0.5

    def cgpa():
        return round(rng.uniform(2.2, 3.95), 2)

    def pct():
        return round(rng.uniform(50, 88), 1)

    # pre-university
    if path == "D" or rng.random() < 0.2:
        degrees.append(Degree(level=DegreeLevel.INTERMEDIATE, title="A-Levels", duration_years=2, completed=True))
        edu_lines.append(("A-Levels", rng.choice(COLLEGES), f"{end_year - 6} - {end_year - 4}", "Grades: A A B"))
    else:
        g = pct()
        degrees.append(Degree(level=DegreeLevel.INTERMEDIATE, title="F.Sc. Pre-Engineering", duration_years=2,
                              completed=True, grade_value=g, grade_scale=GradeScale.PERCENTAGE, grade_scale_max=100))
        edu_lines.append(("F.Sc. Pre-Engineering (HSSC)", rng.choice(COLLEGES),
                          f"{end_year - 6} - {end_year - 4}", f"Marks: {g}%"))

    def add_cgpa_degree(level, field, title, start, end, years, completed):
        v = cgpa()
        mp = rng.choice([2.0, 2.0, 1.0]) if min_pass_shown else None
        d = Degree(level=level, title=title, field=field, institution=rng.choice(UNIS), country="Pakistan",
                   duration_years=years, completed=completed, grade_value=v, grade_scale=GradeScale.CGPA_4,
                   grade_scale_max=4.0, grade_scale_min_pass=mp,
                   expected_completion=date(end, 6, 30) if not completed else None)
        detail = f"CGPA: {v:.2f}/4.00" + (" (up to 7th semester)" if not completed else "")
        if mp:
            detail += f"; minimum passing CGPA {mp:.2f}"
        when = f"{start} - {end}" + (" (expected June %d)" % end if not completed else "")
        degrees.append(d)
        edu_lines.append((title, d.institution, when, detail))

    def add_pct_degree(level, field, title, start, end, years):
        v = pct()
        mp = rng.choice([33.0, 40.0]) if min_pass_shown else None
        d = Degree(level=level, title=title, field=field, institution=rng.choice(UNIS), country="Pakistan",
                   duration_years=years, completed=True, grade_value=v, grade_scale=GradeScale.PERCENTAGE,
                   grade_scale_max=100, grade_scale_min_pass=mp)
        detail = f"Percentage: {v}%" + (f"; pass marks {mp:.0f}%" if mp else "")
        degrees.append(d)
        edu_lines.append((f"{title} ({years:g}-year programme)", d.institution, f"{start} - {end}", detail))

    if path in ("A", "C"):
        f, t = rng.choice(BS_FIELDS)
        bs_end = end_year if path == "A" else end_year - 2
        add_cgpa_degree(DegreeLevel.BACHELOR, f, t, bs_end - 4, bs_end, 4, not in_progress)
        if path == "C":
            mf = rng.choice(["Computer Science", "Data Science", "Artificial Intelligence", f])
            add_cgpa_degree(DegreeLevel.MASTER, mf, f"MS {mf}", end_year - 2, end_year, 2, True)
    elif path == "D":
        f, t = rng.choice(BE_FIELDS)
        add_cgpa_degree(DegreeLevel.BACHELOR, f, t, end_year - 4, end_year, 4, not in_progress)
    else:
        add_pct_degree(DegreeLevel.BACHELOR, "Physics and Mathematics", "B.Sc. (Physics, Mathematics)",
                       end_year - 4, end_year - 2, 2)
        mf = rng.choice(["Computer Science", "Physics", "Mathematics"])
        if rng.random() < 0.5:
            add_pct_degree(DegreeLevel.MASTER, mf, f"M.Sc. {mf}", end_year - 2, end_year, 2)
        else:
            add_cgpa_degree(DegreeLevel.MASTER, mf, f"M.Sc. {mf}", end_year - 2, end_year, 2, True)

    # English
    tests, eng_line = [], None
    r = rng.random()
    if r < 0.45:
        overall = rng.choice([5.5, 6.0, 6.5, 7.0, 7.5, 8.0])
        bands = [max(4.5, overall + rng.choice([-1.0, -0.5, 0, 0, 0.5])) for _ in range(4)]
        tests.append(EnglishTest(test="IELTS", overall=overall, min_band=min(bands)))
        eng_line = (f"IELTS Academic: overall {overall} (Listening {bands[0]}, Reading {bands[1]}, "
                    f"Writing {bands[2]}, Speaking {bands[3]})")
    elif r < 0.6:
        score = rng.randint(75, 110)
        tests.append(EnglishTest(test="TOEFL_iBT", overall=score))
        eng_line = f"TOEFL iBT: {score}"
    emi = True if rng.random() < 0.4 else None
    emi_line = "Medium of instruction certificate: bachelor's degree taught entirely in English" if emi else None

    # work experience
    jobs, months, cursor = [], 0, date(end_year, 7, 1)
    for _ in range(0 if in_progress and rng.random() < 0.6 else rng.randint(0, 3)):
        length = rng.choice([2, 3, 6, 12, 18, 24])
        start = cursor
        stop = start + timedelta(days=30.44 * length)
        months += length
        jobs.append((rng.choice(JOBS), rng.choice(COMPANIES), start.strftime("%b %Y"),
                     stop.strftime("%b %Y"), length))
        cursor = stop + timedelta(days=15)

    prof = Profile(profile_id=pid, date_of_birth=dob, nationality=nat, degrees=degrees, english_tests=tests,
                   english_medium_instruction=emi, work_experience_months=months,
                   interests=rng.sample(INTERESTS, 2))
    doc = {"name": name, "email": name.lower().replace(" ", ".") + "@example.com",
           "phone": f"+92 3{rng.randint(0, 4)}{rng.randint(0, 9)} {rng.randint(1000000, 9999999)}",
           "dob": fmt_date(dob, rng.randint(0, 2)) if dob else None, "nationality": demonym,
           "education": edu_lines[::-1], "english": eng_line, "emi": emi_line,
           "jobs": jobs, "interests": prof.interests,
           "skills": rng.sample(["Python", "C++", "SQL", "PyTorch", "React", "MATLAB", "Excel", "Docker"], 4)}
    return prof, doc


def text_blocks(doc):
    blocks = [("Personal Information", [f"Email: {doc['email']}", f"Phone: {doc['phone']}"] +
               ([f"Date of Birth: {doc['dob']}"] if doc["dob"] else []) + [f"Nationality: {doc['nationality']}"])]
    edu = []
    for title, inst, when, detail in doc["education"]:
        edu.append(f"{title} - {inst} ({when})")
        edu.append(f"    {detail}")
    if doc["emi"]:
        edu.append(doc["emi"])
    blocks.append(("Education", edu))
    if doc["english"]:
        blocks.append(("English Language Proficiency", [doc["english"]]))
    if doc["jobs"]:
        blocks.append(("Experience", [f"{j} at {c}, {s} - {e} ({n} months)" for j, c, s, e, n in doc["jobs"]]))
    else:
        blocks.append(("Experience", ["No work experience yet."]))
    blocks.append(("Research Interests", [", ".join(doc["interests"])]))
    blocks.append(("Skills", [", ".join(doc["skills"])]))
    return blocks


def render_pdf(doc, path: Path, layout: int):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    ss = getSampleStyleSheet()
    story = [Paragraph(doc["name"], ss["Title"] if layout != 2 else ss["Heading1"])]
    for head, lines in text_blocks(doc):
        if layout == 1:   # two-column table layout
            body = "<br/>".join(l.replace("&", "&amp;") for l in lines)
            t = Table([[Paragraph(f"<b>{head}</b>", ss["Normal"]), Paragraph(body, ss["Normal"])]],
                      colWidths=[120, 360])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.grey)]))
            story += [t, Spacer(1, 6)]
        else:
            story.append(Paragraph(head.upper() if layout == 2 else head, ss["Heading2"]))
            for l in lines:
                story.append(Paragraph(l.replace("&", "&amp;"), ss["Normal"]))
            story.append(Spacer(1, 4))
    SimpleDocTemplate(str(path), pagesize=A4, topMargin=36, bottomMargin=36).build(story)


def render_docx(doc, path: Path):
    import docx
    d = docx.Document()
    d.add_heading(doc["name"], 0)
    for head, lines in text_blocks(doc):
        d.add_heading(head, level=1)
        for l in lines:
            d.add_paragraph(l.strip())
    d.save(str(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    out = ROOT / "data" / "profiles" / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    for i in range(1, args.n + 1):
        prof, doc = make_profile(i, rng)
        (out / f"{prof.profile_id}.json").write_text(prof.model_dump_json(indent=1, exclude_none=True))
        if i % 4 == 0:
            render_docx(doc, out / f"{prof.profile_id}.docx")
        else:
            render_pdf(doc, out / f"{prof.profile_id}.pdf", layout=i % 3)
    print(f"wrote {args.n} synthetic CVs and gold profiles to {out}")


if __name__ == "__main__":
    main()
