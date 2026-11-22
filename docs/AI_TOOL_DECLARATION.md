# AI tool declaration: ScholarFit (AI-4009 Assignment 3)

Group: Fatima Farrukh (23I-0773), Fatima Shakir (23I-0503), Eshaal Malik (23I-0732). Track: R&D Product.

## Tools used to prepare the proposal and the code

| Tool | Used for | How the output was checked |
| --- | --- | --- |
| Claude (claude.ai chat) | Brainstorming and refining the project idea; drafting the approval email; drafting and editing the proposal, its diagrams and the results appendix; scaffolding the backend (schemas, rule engine, grade conversion, pipelines, retrieval, LLM client), ingestion scripts, evaluation scripts (metrics, experiment runner, report, agreement, error grouping) and the synthetic-CV generator; drafting the labelling guideline and consent form; debugging setup and free-tier API errors; merging the two annotators' label files and listing disagreements; the results slides and the demo cheat sheet | The team read and edited every section of the proposal; all code was run and tested by the team (unit tests in `backend/tests`); every number in the proposal and slides comes from files in `runs/` and `data/labels/` and is reproducible with the scripts listed below; references were checked against their DOIs |
| Claude Code | Building and integrating the web application (Next.js frontend, FastAPI endpoints, Google Calendar OAuth, curator page); reviewing the proposal against the repository before submission | Run and tested by the team in the live application |
| Gemini Flash (Google AI Studio, free tier) | Pre-filling a draft of the CriteriaGold criteria to save typing (`scripts/criteria_gold.py draft`) | Every draft row was checked against the source text by a team member (`checked_by` column) and corrected where wrong; Claude also flagged and fixed date formats and 8 rows (two years-of-education thresholds and six subject-credit rows), which the team reviewed |

## AI inside the product (evaluated, not used for authoring)

Gemini Flash (CV extraction evaluation), Gemini Flash-Lite (application, criteria extraction, eligibility experiment) and gpt-oss-20b on Groq (open-weight comparison) are components of ScholarFit. They are evaluated quantitatively on held-out test sets (Appendix A of the proposal; `runs/a3_main/`).

## What was done by people only

- All 150 ScholarElig pairs were labelled independently by two team members, with no AI pre-fill; the 13 overall disagreements were adjudicated by the team. No language model produced any gold label.
- Eight programme pages whose robots.txt disallows crawling were transcribed manually by the team and lightly restructured into lists. Earlier AI-paraphrased versions of these pages were discarded and not used.
- Terms-of-service checks for each scholarship family.

## Reproducing the reported numbers

- Agreement: `python eval/agreement.py data/labels/pairs_annotatorA.csv data/labels/pairs_annotatorB.csv`
- Eligibility results and significance tests: `python eval/report.py --name a3_main`
- Error analysis: `python scripts/error_groups.py --name a3_main`
- Criteria extraction: `python eval/eval_criteria.py --models gemini-flash-lite gpt-oss-20b --context retrieved full`