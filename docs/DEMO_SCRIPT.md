# ScholarFit Assignment 3 demo script (and backup recording)

This script covers every Table 3 feature in about 6 minutes. Record one full run of it as the backup
video *before* the live demo (see "Backup screen recording" at the end).

## Before the demo (15 minutes earlier)

1. Start the backend with the real model (from `backend/`):
   `..\.venv\Scripts\python -m uvicorn app.main:app --port 8000`
2. Start the frontend (from `frontend/`): `npm run dev`, then open http://localhost:3000.
3. Pick the demo CV: `data/profiles/synthetic/syn001.pdf` (BS Computer Science, CGPA 2.62, IELTS 7.5).
   Run one full check with it before the demo, so the semantic judge answers come from the cache
   (`runs/cache/`) and the live check is fast.
4. Prepare a change notice, so the badge appears (it is marked as simulated on the curator page):
   `.venv\Scripts\python ingest\check_changes.py --simulate-change sh-cs-elte`
   After the demo: `.venv\Scripts\python ingest\check_changes.py --clear-simulated`
5. In the browser, clear the site data for localhost:3000 if you want a fresh dashboard.

## Live run

| # | Step | Table 3 feature shown |
|---|------|-----------------------|
| 1 | Home page: upload `syn001.pdf`, press **Read CV**. | CV upload and extraction |
| 2 | Point at the amber fields ("Not found in your CV, add it if you have it"). Fill one in, for example the minimum passing grade. Choose **Degree I am applying for: Master's**. Show that **Step 2: Check eligibility** is disabled. Press **I have checked my profile**. | Profile review screen (F1) |
| 3 | Press **Check eligibility**. Results appear programme by programme. | |
| 4 | Read the blue notice at the top (eligibility only; admission is separate; the official page is authoritative). | Notices |
| 5 | Show the groups: Eligible, Conditionally eligible, Not enough information, then **Deadline passed** in grey at the bottom. Tick **Show programmes I don't qualify for**. Read the ranking sentence (60% relevance, 25% funding, 15% urgency) and the hint chips ("Full scholarship", "Close to your field"). | Ranking (F5), outdated handling |
| 6 | On a top programme, press **Why? Show breakdown**. Walk through Requirement / Your profile / Result / Evidence: the quote from the call, the official-call link and snapshot date. Point at a "Checked by a person" row (document or admission requirement), and at a conditional row if there is one. | Requirement breakdown (F3) |
| 7 | Below it, **What you still need**: tick an item. | Missing-requirements panel (F8) |
| 8 | Show the orange **"Call changed on ..., criteria under review"** badge on *MSc Computer Science (Budapest, course 441)*. | Change badge (F10) |
| 9 | Press **Save** on two or three programmes, including one with "Not enough information". | |
| 10 | Open **My dashboard**: saved programmes table, upcoming deadlines (with **.ics** / **Add deadline**), open items, and the **Past checks** table. | Dashboard (F9) |
| 11 | Back on the home page, add the missing information (for example a date of birth or an English test), confirm the profile again, then on the dashboard press **Re-check saved programmes**: the card shows **"Changed: Not enough information → Eligible"**. | Status changes |
| 12 | Open **Curator review**: the changed page is listed at the top, then the criteria waiting for approval. | Change detection, human approval |
| 13 | Optional, in a terminal: show the raw `/api/check` row at http://localhost:8000/docs and point at `outdated` and `missing`. | API returns outdated and missing |

## If something fails live

- The LLM is slow or down: the check still runs. Rule-based criteria are decided without the model,
  and cached answers are reused. If the check fails entirely, switch to the backup video.
- Google Calendar is not connected: use the **.ics** button instead.

## Backup screen recording

- Windows: press **Win + Alt + R** (Xbox Game Bar) to start and stop recording the browser window,
  or use OBS Studio (Display Capture, 1080p, 30 fps). Turn notifications off first.
- Record steps 1 to 12 in one take (about 6 minutes) and narrate as in the live demo.
- Save it as `ScholarFit_demo_backup.mp4` somewhere outside the repository (videos do not belong in
  git), and keep a copy on a USB stick or in cloud storage, so it can be played without the laptop.
