# ScholarFit labelling guideline (v1.1)

Freeze this file before the first experiment run. Record any later change, and the date,
in the changelog at the bottom. Labels are made by people only. Never copy a label from
ScholarFit, from a language model or from another annotator's sheet.

## 1. What is labelled

| Dataset | Unit | Labels |
| --- | --- | --- |
| CriteriaGold | one eligibility criterion of one programme | the schema fields (type, handling, values, grade rule, source quote) |
| ScholarElig | one profile–programme pair | a label per criterion type, plus an overall label |

The question for ScholarElig is always: **"Is this student eligible to APPLY, based only on
this call text and this profile?"** It is never "will they win the scholarship?".

## 2. Labels

| Label | Use when |
| --- | --- |
| `E` (eligible) | the call states the requirement and the profile clearly meets it |
| `NE` (not eligible) | the call states the requirement and the profile clearly fails it |
| `II` (insufficient information) | the call or the profile does not let a careful reader decide |
| `NA` | this criterion type does not appear in the call |

Overall label: `NE` if any type is `NE`; otherwise `II` if any type is `II`; otherwise `E`.

## 3. Decision rules for hard cases

**Selection stages are not eligibility.** Interviews, olympiad rounds (Open Doors),
entrance tests, embassy screening rounds and recommendation letters are recorded in
CriteriaGold with `handling = manual_check`. They do not change the overall label.

**Requirements a CV cannot show** must be met before applying but cannot be checked from
a CV: medical fitness, embassy nomination, a "No Objection Certificate", a statement of
purpose. If the call makes them a condition of eligibility, they are `manual_check` too.
They are listed for the student but are not scored.

**Deadlines are not eligibility.** Deadline criteria are recorded but never labelled.

**Grades:**
1. If the requirement is on the student's own scale (e.g. "CGPA 3.0/4.0" and the student
   has CGPA on 4.0), compare directly.
2. If the scales differ, use ONLY the conversion rule the programme itself states:
   modified Bavarian formula, a WES table, a UK-class mapping, or a country table such as
   "Pakistan: CGPA 3.0 or 60%". Record that rule in CriteriaGold `grade_rule`.
3. If the scales differ and no rule is stated, label `II`. Never convert with a formula you
   choose yourself (supervisor point 2).
4. Modified Bavarian: German grade = 1 + 3 × (Nmax − Nd) / (Nmax − Nmin). If the CV does not
   state the minimum passing grade (Nmin), label `II`.
5. For a final-year student, use the CGPA shown up to the latest semester only if the call
   allows final-year applicants; otherwise follow rule 6.

**Final-year students:** if the call says final-year students may apply, the degree
counts. If it says they may not, label `NE`. If it says nothing, label `II`.

**Years of education:** count 12 years for Matric + FSc/A-levels, then add the nominal
length of each completed tertiary degree (BS 4, old BSc 2, MSc 2, MS 2). "16 years or
equivalent" decides by this count unless the programme defines equivalence differently,
in which case follow the programme.

**Credits:** "180 ECTS or equivalent" counts 60 ECTS per full-time year (ECTS Users'
Guide), unless the call or the CV states the credits.

**Age:** use the reference date the call gives. If none is given, use the application
deadline. "Under 35" means 34 or younger on that date; "not older than 35" means 35 or
younger. Missing date of birth → `II`.

**English:** a stated minimum test score is compared with the profile's score, and
sub-scores too if the call gives them. If the call allows a medium-of-instruction waiver
and the CV shows an English-medium certificate, label `E`. If the call requires a test,
the profile has none and no waiver applies, label `NE`. If a waiver might apply but the CV
does not say, label `II`. "Good command of English" with no score → `II`.

**Field of study:** label `E` if the field is named in the call or obviously the same
(Software Engineering for "Computer Science or related"). Label `NE` if clearly unrelated
(English Literature for a Computer Science master's). Otherwise label `II`, and write a
note.

**Nationality:** "developing countries" or "partner countries" lists count only if the
list is in the snapshot text; otherwise `II`.

**Alternatives (any of).** If the call gives alternatives ("IELTS 6.5 or an English-medium
degree", "180 ECTS or a four-year bachelor's degree"), label `E` when any one alternative is
clearly met, `NE` only when every alternative clearly fails, otherwise `II`.

**Track-specific requirements.** Some calls set different requirements per track or target
degree (MEXT: 16 years for the master's track, 18 for the doctoral track; GKS: embassy vs
university track). Apply only the track the student would apply for: the next degree above
their highest completed degree (a bachelor holder applies for a master's). Write the track in
`notes`. Never apply a requirement of another track.

**Conditional eligibility.** If the call itself states a condition the student can still meet
before the programme starts (graduating before the start date, submitting an English-medium
certificate for a waiver), label `E` and write `conditional: <the condition>` in `notes`.

**Documents.** Transcripts, attestation, recommendation letters and certificates are not
labelled. Only if the call makes a document an eligibility condition is it `manual_check`.
A document that is missing from the profile never changes the label.

**Clarifications from the challenge-set adjudication (2026-11-24).**
- *Credits and duration:* one year of full-time study is 60 ECTS (the ECTS definition). A 4-year
  bachelor's is 240 ECTS and meets "180 ECTS"; a 2-year B.Sc. is 120 ECTS and fails it. A 2-year
  B.Sc. plus 2-year M.Sc. counts as one 3-year degree only if the call says so; otherwise `II`.
- *Track:* the student applies for the next degree above their highest completed degree, so a
  master's holder is on the doctoral track.
- *Public facts:* a fact anyone can check that the call refers to without listing it (for example
  whether Pakistan has diplomatic relations with Japan) is used; do not label it `II`.
- *Type of experience:* if the call needs a particular kind of work (for example teaching) and the
  profile gives only months of work, label `II`.
- *Where a degree was taken:* the degree's country in the profile counts. An exemption for degrees
  taught in English in listed countries fails for a degree taken in Pakistan.
- *Explicit wording wins:* "applicants who already hold a degree" excludes final-year students
  (`NE`); a call that is silent on final-year students gives `II` for an unfinished degree.
- *Rank or class position* (for example "top 10% of the class") is an eligibility condition; if
  the profile does not give it, `II`.

**Missing profile information.** If the call states a requirement and the profile does not
give the value (no grade, no nationality, no dates for work experience), label `II`.

## 4. Procedure

1. Read the programme text in the snapshot only, never the live website.
2. Read the profile JSON, not the rendered CV. The CV is tested separately.
3. Fill the per-type columns first, then derive the overall label with rule 2.
4. Put the sentence you relied on in the `evidence` column, and any doubt in `notes`.
5. Agreement round: two annotators label the same 20% of pairs separately. Compute
   Cohen's kappa with `python eval/agreement.py`, target ≥ 0.7. Discuss each disagreement,
   update this guideline if a rule was unclear, and only then label the rest.
6. Development pairs (`split = dev`) may be used to write prompts. Test pairs must not be
   opened by whoever writes prompts until the prompts are frozen.

## Changelog
- v1.0 (2026-11-21): first version.
- v1.1 (2026-11-23): rules for alternatives, track-specific requirements, conditional
  eligibility, documents and missing profile information, written after the supervisor's
  feedback and the first error analysis. Used for the challenge set; the 150 main pairs keep
  their v1.0 labels, and any pair whose label would change under v1.1 is listed separately.
