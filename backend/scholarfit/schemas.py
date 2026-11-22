"""Data schemas shared by every part of ScholarFit.

The general criteria schema is the heart of the project: every scholarship call,
whatever its format, is mapped into a list of `Criterion` objects. Criteria that do
not fit a core type are kept as type OTHER with a handling mode (semantic or
manual_check) instead of being dropped.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- labels
class Label(str, Enum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT = "insufficient_info"
    MANUAL = "manual_check"  # selection stages (interview, olympiad round): shown, not scored
    CONDITIONAL = "conditional"  # met if a condition stated in the call is satisfied (scored as eligible)


EVAL_LABELS = [Label.ELIGIBLE.value, Label.NOT_ELIGIBLE.value, Label.INSUFFICIENT.value]


# --------------------------------------------------------------------------- profile
class GradeScale(str, Enum):
    CGPA_4 = "cgpa_4"
    CGPA_5 = "cgpa_5"
    PERCENTAGE = "percentage"
    UK_CLASS = "uk_class"
    GERMAN = "german"          # 1.0 best, 4.0 lowest pass
    OTHER = "other"


class DegreeLevel(str, Enum):
    SECONDARY = "secondary"          # Matric / O-levels
    INTERMEDIATE = "intermediate"    # FSc / ICS / A-levels (12 years)
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


class Degree(BaseModel):
    level: DegreeLevel
    title: Optional[str] = None                 # e.g. "BS Computer Science"
    field: Optional[str] = None                 # e.g. "Computer Science"
    institution: Optional[str] = None
    country: Optional[str] = None
    duration_years: Optional[float] = None      # nominal length of the programme
    completed: Optional[bool] = None
    expected_completion: Optional[date] = None
    grade_value: Optional[float] = None
    grade_scale: Optional[GradeScale] = None
    grade_scale_max: Optional[float] = None     # e.g. 4.0 or 100
    grade_scale_min_pass: Optional[float] = None  # needed for the modified Bavarian formula
    uk_class: Optional[str] = None              # "first", "upper_second", "lower_second", "third"
    ects: Optional[float] = None


class EnglishTest(BaseModel):
    test: str                                   # IELTS, TOEFL_iBT, PTE, Duolingo
    overall: float
    min_band: Optional[float] = None            # lowest sub-score, if known
    test_date: Optional[date] = None


class Profile(BaseModel):
    profile_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    degrees: list[Degree] = Field(default_factory=list)
    english_tests: list[EnglishTest] = Field(default_factory=list)
    english_medium_instruction: Optional[bool] = None  # bachelor taught in English (certificate)
    work_experience_months: Optional[int] = None
    interests: list[str] = Field(default_factory=list)
    target_level: Optional[DegreeLevel] = None   # degree applied for; default: next above the highest completed

    def highest(self, level: DegreeLevel | None = None) -> Optional[Degree]:
        order = [DegreeLevel.SECONDARY, DegreeLevel.INTERMEDIATE, DegreeLevel.BACHELOR,
                 DegreeLevel.MASTER, DegreeLevel.PHD]
        pool = [d for d in self.degrees if level is None or d.level == level]
        if not pool:
            return None
        return max(pool, key=lambda d: order.index(d.level))


# --------------------------------------------------------------------------- criteria
class CriterionType(str, Enum):
    MIN_GRADE = "min_grade"
    YEARS_OF_EDUCATION = "years_of_education"
    MIN_CREDITS = "min_credits"           # e.g. 180 ECTS
    DEGREE_LEVEL = "degree_level"
    DEGREE_FIELD = "degree_field"         # semantic
    AGE_LIMIT = "age_limit"
    NATIONALITY = "nationality"
    ENGLISH_TEST = "english_test"
    WORK_EXPERIENCE = "work_experience"
    DEADLINE = "deadline"                 # informational, never decides eligibility
    DOCUMENT = "document"                 # a document to prepare: listed, never judged
    ADMISSION = "admission"               # host-university admission requirement: manual check
    OTHER = "other"


class Handling(str, Enum):
    AUTO = "auto"                 # decided by the rule engine
    SEMANTIC = "semantic"         # decided by the LLM judge, with citation or abstention
    MANUAL = "manual_check"       # selection stage or unverifiable from a CV


class GradeRule(str, Enum):
    SAME_SCALE = "same_scale"                 # requirement on the student's own scale
    MODIFIED_BAVARIAN = "modified_bavarian"   # German grade conversion
    WES_GPA = "wes_gpa"                       # WES table, loaded from data/conversion_tables
    UK_CLASS_MAPPING = "uk_class_mapping"     # programme-stated mapping of UK classes
    PERCENTAGE_THRESHOLD = "percentage_threshold"
    PROGRAMME_TABLE = "programme_table"       # programme gives thresholds per scale
    NOT_STATED = "not_stated"


class ScaleThreshold(BaseModel):
    scale: GradeScale
    min_value: float


class Criterion(BaseModel):
    criterion_id: Optional[str] = None
    type: CriterionType
    handling: Handling = Handling.AUTO
    track: Optional[DegreeLevel] = None       # applies only to applicants for this degree (e.g. MEXT doctoral track)
    any_of: Optional[str] = None              # criteria sharing this group id are alternatives
    condition: Optional[str] = None           # a condition stated in the call (e.g. "graduate before 1 October")
    text: str = ""                            # the requirement in plain words
    source_quote: Optional[str] = None        # exact sentence from the call
    source_section: Optional[str] = None      # retrieved section id
    confidence: Optional[float] = None

    # min_grade
    grade_rule: Optional[GradeRule] = None
    grade_min_value: Optional[float] = None
    grade_scale: Optional[GradeScale] = None
    uk_class_min: Optional[str] = None
    thresholds: list[ScaleThreshold] = Field(default_factory=list)  # programme_table / uk mapping
    applies_to_level: Optional[DegreeLevel] = None  # which degree the grade refers to

    # years_of_education / min_credits / work_experience
    min_years: Optional[float] = None
    min_ects: Optional[float] = None
    min_work_months: Optional[int] = None

    # degree_level
    required_level: Optional[DegreeLevel] = None
    final_year_allowed: Optional[bool] = None

    # degree_field
    fields: list[str] = Field(default_factory=list)

    # age_limit
    max_age: Optional[int] = None
    age_reference_date: Optional[date] = None
    born_on_or_after: Optional[date] = None

    # nationality
    nationalities_allowed: list[str] = Field(default_factory=list)
    nationalities_excluded: list[str] = Field(default_factory=list)

    # english_test
    english_min_scores: dict[str, float] = Field(default_factory=dict)   # {"IELTS": 6.5}
    english_min_band: dict[str, float] = Field(default_factory=dict)     # {"IELTS": 6.0}
    english_waiver_medium_of_instruction: Optional[bool] = None

    # deadline
    deadline: Optional[date] = None


class Programme(BaseModel):
    programme_id: str
    family: str                       # erasmus_mundus, daad, commonwealth, hec, csc, ...
    name: str
    url: Optional[str] = None
    snapshot_date: Optional[date] = None
    text: str = ""
    criteria: list[Criterion] = Field(default_factory=list)


# --------------------------------------------------------------------------- verdicts
class CriterionVerdict(BaseModel):
    criterion_id: Optional[str] = None
    type: CriterionType
    label: Label
    reason: str
    rule_used: Optional[str] = None
    citation: Optional[str] = None


class EligibilityResult(BaseModel):
    programme_id: str
    profile_id: Optional[str] = None
    system: str
    overall: Label
    criteria: list[CriterionVerdict] = Field(default_factory=list)
    deadline_open: Optional[bool] = None
    latency_s: Optional[float] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None
