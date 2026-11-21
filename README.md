# ScholarFit

Criterion-level, source-cited scholarship eligibility checking for Pakistani students applying
abroad. AI-4009 Generative AI, R&D Product track. Fatima Farrukh (23I-0773), Fatima Shakir
(23I-0503), Eshaal Malik (23I-0732).

**Research question.** Does a neuro-symbolic pipeline (S2: an LLM extracts each criterion into a
general schema, deterministic code evaluates it) make fewer false "eligible" verdicts than asking
an LLM directly (B1/B2), with identical inputs?

## Repository map

| Path | What it is | AI or code |
| --- | --- | --- |
| `backend/scholarfit/schemas.py` | Profile, general criteria schema, verdicts | code |
| `backend/scholarfit/rules/` | rule engine and grade conversion (modified Bavarian, tables) | code |
| `backend/scholarfit/retrieval.py` | section splitting, BM25, optional dense, RRF, citation check | code (+ embeddings) |
| `backend/scholarfit/llm/client.py` | one client for OpenAI, Gemini, Ollama; JSON validation, retry, cache, cost log | AI plumbing |
| `backend/scholarfit/prompts/` | versioned prompts | AI |
| `backend/scholarfit/pipelines/` | CV extraction, criteria extraction, systems B0, B1, B2, S1, S2 | AI + code |
| `backend/scholarfit/integrations/gcal.py` | Google Calendar + .ics | code |
| `backend/app/main.py` | FastAPI app | code |
| `frontend/` | Next.js student portal and curator screen | code |
| `ingest/` | crawler (robots.txt aware) and parser into a dated snapshot | code |
| `scripts/` | synthetic CVs, pair sampler, CriteriaGold tool, catalogue builder | code |
| `eval/` | experiment runner, metrics, report, CV and criteria evaluations, kappa | code |
| `data/guidelines/` | labelling guideline, consent form | docs |

## Setup

```bash
cp .env.example .env               # add OPENAI_API_KEY and/or GEMINI_API_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && python -m pytest -q && cd ..          # 20 tests, no API key needed
```

Fill the current per-token prices in `config/models.yaml`, otherwise cost per request shows "n/a".
Local model: install [Ollama](https://ollama.com), then `ollama pull qwen2.5:7b-instruct`.

### Run the app

```bash
python scripts/build_catalogue.py --model gemini-flash     # once per snapshot
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3000
```

Or everything in Docker: `docker compose up --build`.
Dry run without data or keys: `SCHOLARFIT_MOCK=1 python scripts/build_catalogue.py --demo`, then start the API with `SCHOLARFIT_MOCK=1`.

## Data pipeline

```bash
# 1. sources: add programme URLs to data/sources.yaml and fill terms_checked per family
python ingest/crawl.py                       # -> data/snapshots/<date>/
#    pages that block crawlers: save as data/programmes/manual/<id>.md (YAML header: id, family, name, url, snapshot_date)
python ingest/parse.py --snapshot <date>     # -> data/programmes/programmes.jsonl

# 2. profiles: 50 synthetic CVs with exact gold profiles (already generated, seed 7)
python scripts/make_synthetic_cvs.py --n 50 --seed 7
#    real CVs (consent form in data/guidelines): data/profiles/real/<id>.pdf + hand-made <id>.json; never commit

# 3. CriteriaGold: LLM draft -> people check every row -> gold
python scripts/criteria_gold.py draft --model gemini-flash
#    edit data/labels/criteria_checked.csv (set checked_by on every row)
python scripts/criteria_gold.py build
python scripts/criteria_gold.py corrections

# 4. ScholarElig pairs (programme-level dev/test split, stratified by family)
python scripts/make_pairs.py --n 200
#    label data/labels/pairs.csv by hand following data/guidelines/labelling_guideline.md
#    double-label 20%: save copies as pairs_annotatorA.csv / pairs_annotatorB.csv, then
python eval/agreement.py data/labels/pairs_annotatorA.csv data/labels/pairs_annotatorB.csv
```

## Evaluation (Stage D)

```bash
# CV-to-profile vs the rule-based baseline (field accuracy, schema-valid rate, latency, cost)
python eval/eval_cv.py --models gemini-flash gpt-oss-20b
# criteria extraction alone, retrieved sections vs full page
python eval/eval_criteria.py --models gemini-flash gpt-oss-20b --context retrieved full
# research experiment: B1 vs S2, one API + one local model, 3 runs
python eval/run_experiment.py --name a3_first --systems B0 B1 S2 --models gemini-flash gpt-oss-20b --runs 3
python eval/report.py --name a3_first      # report.md, summary.csv, per_type.csv, failures.csv, fer.png
```

Every model call is logged to `runs/llm_calls.jsonl` (latency, tokens, cost, retries, failures).
Responses are cached in `runs/cache/` so re-running a report costs nothing; repeated runs use
different seeds. Use `--no-cache` for latency measurements on fresh calls.

## AI tool declaration

See `docs/AI_TOOL_DECLARATION.md`.
