# Plan to finish Assignment 3 (Saturday to Sunday)

Each person commits their own part from their own GitHub account: rubric C6 needs commits from
every member. Push the scaffold first, then work on branches and merge through pull requests.

| Step | Who (suggested) | Command or task | Output |
| --- | --- | --- | --- |
| 1 | Eshaal | Create the GitHub repo, push this code, give the instructor access, add `.env` locally | repo link |
| 2 | Fatima Farrukh | Add about 60 programme URLs (5 per family) to `data/sources.yaml`, check terms, crawl and parse; save blocked pages by hand into `data/programmes/manual/` | `programmes.jsonl` |
| 3 | Fatima Shakir | Set up Ollama with `qwen2.5:7b-instruct`, fill prices in `config/models.yaml`, run `eval/eval_cv.py` on the 50 synthetic CVs | CV results (component 1) |
| 4 | Eshaal | `criteria_gold.py draft`, then all three check rows (about 100 criteria from about 15 programmes); `build` | CriteriaGold |
| 5 | Fatima Farrukh | `make_pairs.py --n 200`; everyone labels about 70 pairs; two people double-label 40; `agreement.py` | labelled pairs, kappa |
| 6 | Eshaal | `run_experiment.py --name a3_first --systems B0 B1 S2 --models gemini-flash gpt-oss-20b --runs 3`, then `report.py` | research results (D6) |
| 7 | Fatima Shakir | `eval_criteria.py --context retrieved full` | extraction results (component 2) |
| 8 | Fatima Shakir | `build_catalogue.py`, Google Calendar OAuth client, run the app end to end, deploy or check that `docker compose up` works | live demo |
| 9 | All | Group at least 10 failures per component by cause in `failures.csv`; build 6 to 8 results slides from the reports | demo slides |
| 10 | All | Fill in the AI tool declaration; rehearse: each person presents a part and can explain all code | viva ready |

If labelling time runs short: 150 pairs is still enough for a first experiment; keep at least 50
per component and say so honestly in the demo.
