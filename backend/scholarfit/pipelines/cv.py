"""CV -> structured Profile.

`extract_profile_llm` is the AI component; `extract_profile_rules` is the simple
rule-based baseline it is compared with (Technical Alternatives, Section 6).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from ..llm.client import CallMeta, chat_json
from ..schemas import Degree, DegreeLevel, EnglishTest, GradeScale, Profile
from .common import build_messages


def read_cv_text(path: str | Path) -> str:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".pdf":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    if suf == ".docx":
        import docx
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    return path.read_text(errors="ignore")


def extract_profile_llm(cv_text: str, model: str, use_cache: bool = True, run_tag: str = "",
                        profile_id: Optional[str] = None) -> tuple[Profile, CallMeta]:
    msgs = build_messages("cv_extract", cv_text=cv_text[:12000])
    prof, meta = chat_json(msgs, Profile, component="cv_extract", model=model,
                           use_cache=use_cache, run_tag=run_tag)
    prof.profile_id = profile_id
    return prof, meta


# --------------------------------------------------------------------------- baseline
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _parse_date(s: str) -> Optional[date]:
    s = s.strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"(\d{1,2})[/\-. ](\d{1,2})[/\-. ](\d{4})", s)
    if m:
        return date(int(m[3]), int(m[2]), int(m[1]))
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", s)
    if m and m[2].lower() in MONTHS:
        return date(int(m[3]), MONTHS[m[2].lower()], int(m[1]))
    return None


def extract_profile_rules(cv_text: str, profile_id: Optional[str] = None) -> Profile:
    """Regex baseline. Intentionally simple: it is the 'no AI' reference point."""
    t = cv_text
    dob = None
    m = re.search(r"(?:date of birth|dob|born)\s*[:\-]?\s*([0-9A-Za-z ,./\-]{8,20})", t, re.I)
    if m:
        dob = _parse_date(m[1].replace(",", " "))
    nat = None
    m = re.search(r"nationality\s*[:\-]?\s*([A-Za-z]+)", t, re.I)
    if m:
        nat = "Pakistan" if m[1].lower().startswith("pakistan") else m[1].title()
    degrees = []
    if re.search(r"\b(F\.?Sc|ICS|I\.?Com|A[- ]Levels?|HSSC|Intermediate)\b", t, re.I):
        degrees.append(Degree(level=DegreeLevel.INTERMEDIATE, duration_years=2, completed=True))
    m = re.search(r"\b(BS|B\.?Sc|BE|B\.?E|BBA|B\.?Tech|Bachelor)[^\n]{0,80}", t, re.I)
    if m:
        g = re.search(r"CGPA[^0-9]{0,10}([0-4]\.\d{1,2})\s*/\s*([45](?:\.0+)?)", t, re.I)
        pct = re.search(r"(\d{2}(?:\.\d+)?)\s*%", t)
        deg = Degree(level=DegreeLevel.BACHELOR, title=m[0].strip()[:60], completed=True)
        if g:
            deg.grade_value, deg.grade_scale_max = float(g[1]), float(g[2])
            deg.grade_scale = GradeScale.CGPA_4 if float(g[2]) == 4 else GradeScale.CGPA_5
        elif pct:
            deg.grade_value, deg.grade_scale, deg.grade_scale_max = float(pct[1]), GradeScale.PERCENTAGE, 100.0
        dur = re.search(r"(\d)[- ]year", m[0], re.I)
        deg.duration_years = float(dur[1]) if dur else (4.0 if m[1].upper().startswith(("BS", "BE", "B.E")) else None)
        degrees.append(deg)
    tests = []
    m = re.search(r"IELTS[^0-9]{0,25}(\d(?:\.\d)?)", t, re.I)
    if m:
        tests.append(EnglishTest(test="IELTS", overall=float(m[1])))
    m = re.search(r"TOEFL[^0-9]{0,25}(\d{2,3})", t, re.I)
    if m:
        tests.append(EnglishTest(test="TOEFL_iBT", overall=float(m[1])))
    return Profile(profile_id=profile_id, date_of_birth=dob, nationality=nat, degrees=degrees,
                   english_tests=tests)
