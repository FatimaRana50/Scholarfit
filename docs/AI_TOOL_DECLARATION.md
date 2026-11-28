# AI tool declaration: ScholarFit (AI-4009 Assignment 3)

Group: Fatima Farrukh (23I-0773), Fatima Shakir (23I-0503), Eshaal Malik (23I-0732). Track: R&D Product. Updated 28 November 2026.

## Tools used to prepare the proposal and the code

| Tool | Used for | How the output was checked |
| --- | --- | --- |
| Claude (claude.ai chat) | Brainstorming and refining the project idea; drafting the approval email; drafting and editing the proposal, its diagrams and the results appendix; scaffolding the backend (schemas, rule engine, grade conversion, pipelines, retrieval, LLM client), ingestion scripts, evaluation scripts (metrics, experiment runner, report, agreement, error grouping) and the synthetic-CV generator; drafting the labelling guideline and consent form; debugging setup and free-tier API errors; merging the two annotators' label files and listing disagreements; the results slides and the demo cheat sheet | The team read and edited every section of the proposal; all code was run and tested by the team (unit tests in `backend/tests`); every number in the proposal and slides comes from files in `runs/` and `data/labels/` and is reproducible with the scripts listed below; references were checked against their DOIs |
| Claude (claude.ai chat), second round after the supervisor's feedback | Revising the proposal for the feedback and checking that the literature was current; the schema and rule-engine extension (track, any-of and condition fields, document and admission items, conditional verdicts, missing-requirements list) with its unit tests; the challenge-set generator (`scripts/make_challenge_set.py`) and labelling packs (`scripts/labelling_pack.py`); marking and re-running failed model calls (`scripts/mark_failed_calls.py`); page-change detection (`ingest/check_changes.py`); the round-2 error grouping (`scripts/error_groups_v2.py`); drafting guideline v1.1 wording from the team's adjudication decisions; merging the two challenge-set label files and listing disagreements; the brief for the app features (`docs/APP_V2_BRIEF.md`); updating Appendix A, the slides and the cheat sheet with the second-round results | Code run and tested by the team (28 unit tests pass); the rerun of failed calls was checked to leave no pair in error; Table A8 counts were reproduced with `scripts/error_groups_v2.py`; the team read and edited all changed text |
| Claude Code | Building and integrating the web application (Next.js frontend, FastAPI endpoints, Google Calendar OAuth, curator page, and the second-round app features: profile review, requirement breakdown, missing-requirements panel, ranking, dashboard, change badges); reviewing the proposal against the repository before submission | Run and tested by the team in the live application |
| Gemini Flash (Google AI Studio, free tier) | Pre-filling a draft of the CriteriaGold criteria to save typing (`scripts/criteria_gold.py draft`) | Every draft row was checked against the source text by a team member (`checked_by` column) and corrected where wrong; Claude also flagged and fixed date formats and 8 rows (two years-of-education thresholds and six subject-credit rows), which the team reviewed |

## AI inside the product (evaluated, not used for authoring)

Gemini Flash (CV extraction evaluation), Gemini Flash-Lite (application, criteria extraction, semantic judge, eligibility experiments) and gpt-oss-20b on Groq (open-weight comparison) are components of ScholarFit, used in systems B1, S1 and S2. They are evaluated quantitatively on held-out test sets: the first experiment in `runs/a3_main/`, and the second experiment on the original test split in `runs/v2_main/` and on the challenge set in `runs/v2_chal/` (Appendix A of the proposal).

## What was done by people only

- All 150 ScholarElig pairs were labelled independently by two team members, with no AI pre-fill; the 13 overall disagreements were adjudicated by the team.
- All 78 challenge-set pairs were labelled independently by two team members using guideline v1.1, with no AI pre-fill (83.3% agreement, Cohen's kappa 0.73); the disagreements were adjudicated by the team, and the team decided the guideline clarifications that came out of the adjudication. The challenge profiles themselves were produced by a deterministic script from scenario templates, not by a language model.
- No language model produced any gold label in either set.
- Eight programme pages whose robots.txt disallows crawling were transcribed manually by the team and lightly restructured into lists. Earlier AI-paraphrased versions of these pages were discarded and not used.
- Terms-of-service checks for each scholarship family.

## Reproducing the reported numbers

- Agreement, main set: `python eval/agreement.py data/labels/pairs_annotatorA.csv data/labels/pairs_annotatorB.csv`
- First experiment: `python eval/report.py --name a3_main`; error analysis `python scripts/error_groups.py --name a3_main`
- Second experiment: `python eval/report.py --name v2_main` and `python eval/report.py --name v2_chal`; error analysis `python scripts/error_groups_v2.py --name v2_chal`
- Criteria extraction: `python eval/eval_criteria.py --models gemini-flash-lite gpt-oss-20b --context retrieved full`