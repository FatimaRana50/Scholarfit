# ScholarFit app v2: features for Assignment 3 (due 28 November)

For Fatima Shakir, to build in Claude Code. The supervisor's feedback asks for 60–75% of the product.
The engine work (conditional verdicts, alternatives, track-specific rules, the to-do list) is
already in the backend; this brief covers the app. Build in this order; each item is small on its own.

Rule for every feature: **the language model never decides anything in the app.** Verdicts come
from `scholarfit.rules.engine`. The app only displays, stores and sorts.

## 0. Backend change to `/api/check` (do this first)

In `backend/app/main.py`, inside `check()`:

```python
from scholarfit.rules.engine import evaluate, missing_requirements

ORDER = {Label.ELIGIBLE: 0, Label.CONDITIONAL: 1, Label.INSUFFICIENT: 2, Label.NOT_ELIGIBLE: 3}

# in the loop, add two keys to `row`:
"outdated": bool(deadline and deadline < today),     # F10: show, but never list as eligible
"missing": missing_requirements(res, crits),         # F8: what the student still needs

# sort: outdated last, then by verdict, then by ranking score (section 4)
```

The label `conditional` is new (e.g. a final-year student who must graduate before the start
date). Show it as **"Conditionally eligible"** with the condition text from the criterion's `reason`.

## 1. Profile review gate (F1)

- After CV extraction, show the editable profile and a **"I have checked my profile"** button.
- The **Check** button stays disabled until it is pressed.
- Highlight empty fields in amber with "Not found in your CV, add it if you have it": date of birth,
  nationality, grades, minimum passing grade, English test, work experience.
- Add a **"Degree I am applying for"** select (master's / PhD); send it as `profile.target_level`.
  The engine uses it for track-specific rules (MEXT master's vs doctoral track).

## 2. Requirement breakdown (F3)

For each programme, one table:

| Requirement | Your profile | Result | Evidence |
| --- | --- | --- | --- |
| Minimum grade 2.5 (German scale, modified Bavarian) | CGPA 3.40 / 4.00 → 1.9 | Met | "quote from the call" |

- **Requirement** = criterion `text`; **Your profile** = the matching profile value; **Result** =
  verdict (Met / Not met / Conditionally met / Not enough information / Checked by a person);
  **Evidence** = `citation`, plus a link to the source URL and the snapshot date.
- Never show a verdict without its evidence quote.

## 3. "What you still need" panel (F8)

Use the `missing` list from `/api/check`, already sorted: `not_met`, `missing_info`, `condition`,
`document`, `manual`. Show it under the breakdown with a checkbox per item, and on the dashboard.

## 4. Ranking (F5)

The ranking orders programmes, it does not score the student. Sort by:

1. not outdated before outdated;
2. overall verdict: eligible, conditionally eligible, not enough information (hide not eligible
   behind a "Show programmes I don't qualify for" toggle);
3. within a group, by `score = 0.6 * relevance + 0.25 * funding + 0.15 * urgency`:
   - `relevance`: cosine similarity (0 to 1) between the student's degree field + interests and the
     programme name + first 2,000 characters of its text. Use the embedding model already in
     `scholarfit/retrieval.py` if installed, otherwise TF-IDF from scikit-learn.
   - `funding`: 1.0 full scholarship, 0.6 partial, 0.3 tuition only, 0.5 unknown. Add
     `funding: full|partial|tuition` per programme in `data/sources.yaml` where the call says it.
   - `urgency`: 1.0 if the deadline is within 30 days, 0.5 within 90 days, 0.2 later, 0 unknown.

Keep the weights in one config dict; we tune them later. Show no score number to the student.

## 5. Dashboard (F9)

New page `/dashboard`. New SQLite table in `backend/scholarfit/store.py`:

```sql
CREATE TABLE IF NOT EXISTS saved (profile_id TEXT, programme_id TEXT, saved_at REAL,
  last_overall TEXT, last_checked REAL, PRIMARY KEY (profile_id, programme_id));
```

Endpoints: `POST /api/saved` (save a programme), `GET /api/saved?profile_id=`,
`DELETE /api/saved/{programme_id}`.

Dashboard cards: saved programmes with their verdict; upcoming deadlines (with the existing
Add-to-Google-Calendar button); open items from "What you still need"; and **status changes**: on
each new check, compare the new overall verdict with `last_overall`, show "Changed: Not enough
information → Eligible" when it differs, then update `last_overall`.

## 6. Change detection (F10)

- Run `python ingest/check_changes.py` after a re-crawl and parse. It writes
  `data/programmes/changes.json` with `changed`, `new` and `removed` programmes.
- Add `GET /api/changes` that returns that file.
- In results and the dashboard, show a badge **"Call changed on <date>, criteria under review"**
  for programmes in `changed`. On the curator page, list them at the top.
- Outdated programmes (deadline passed) get a grey **"Deadline passed"** badge and are never in the
  eligible group.

## 7. Notices (supervisor points 4 and 6)

Show on every results page, near the top:

> ScholarFit checks the scholarship's stated eligibility conditions only. Meeting them means you
> may apply; it does not mean you are a competitive applicant or that you will be selected.
> Admission to the host university is decided separately by the university. The official
> programme page is always authoritative.

Admission requirements (criterion type `admission`) appear in the breakdown as "Checked by a
person: admission requirement of the host university".

## 8. Done when

- A fresh CV goes: upload → review gate → check → ranked results with breakdown, evidence and
  "what you still need" → save → dashboard shows deadline and open items → calendar works.
- `check_changes.py` changes show as badges.
- Each feature is in its own commit from your GitHub account.
