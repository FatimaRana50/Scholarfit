# Results: a3_main

109 pairs, runs per condition: 1

| System | Model | accuracy | macro_f1 | false_eligible_rate | false_not_eligible_rate | under_abstention | risky_under_abstention | over_abstention | p50 latency (s) | p95 latency (s) | cost / pair (USD) | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | none | 0.505 | 0.363 | 0.028 | 0.000 | 0.317 | 0.183 | 0.694 | 0.00 | 0.01 | 0.00000 | 0 |
| B1 | gemini-flash | 0.474 | 0.477 | 0.000 | 0.000 | 0.667 | 0.222 | 0.400 | 61.34 | 291.37 | n/a (set prices) | 1 |
| B1 | gemini-flash-lite | 0.651 | 0.606 | 0.056 | 0.000 | 0.450 | 0.183 | 0.184 | 6.09 | 12.97 | 0.00000 | 0 |
| B1 | gpt-oss-20b | 0.569 | 0.527 | 0.028 | 0.462 | 0.533 | 0.100 | 0.163 | 3.40 | 61.81 | 0.00000 | 0 |
| S2 | gemini-flash-lite | 0.394 | 0.316 | 0.000 | 0.692 | 0.733 | 0.017 | 0.265 | 5.71 | 18.13 | 0.00000 | 0 |
| S2 | gpt-oss-20b | 0.450 | 0.349 | 0.000 | 0.692 | 0.733 | 0.033 | 0.143 | 2.43 | 68.73 | 0.00000 | 0 |
| S2-oracle | gemini-flash-lite | 0.500 | 0.450 | 0.000 | 0.667 | 0.562 | 0.000 | 0.083 | 0.02 | 17.98 | 0.00000 | 0 |
| S2-oracle | gpt-oss-20b | 0.536 | 0.475 | 0.000 | 0.667 | 0.500 | 0.000 | 0.083 | 2.49 | 41.19 | 0.00000 | 0 |

## Confusion matrices (run 0; rows = gold, columns = predicted)

**B0 / none**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 0 | 0 | 13 |
| NE | 1 | 14 | 21 |
| II | 11 | 8 | 41 |

**B1 / gemini-flash**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 0 | 0 |
| NE | 0 | 5 | 4 |
| II | 2 | 4 | 3 |

**B1 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 7 | 0 | 6 |
| NE | 2 | 31 | 3 |
| II | 11 | 16 | 33 |

**B1 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 5 | 6 | 2 |
| NE | 1 | 29 | 6 |
| II | 6 | 26 | 28 |

**S2 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 9 | 3 |
| NE | 0 | 26 | 10 |
| II | 1 | 43 | 16 |

**S2 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 9 | 3 |
| NE | 0 | 32 | 4 |
| II | 2 | 42 | 16 |

**S2-oracle / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 4 | 1 |
| NE | 0 | 6 | 0 |
| II | 0 | 9 | 7 |

**S2-oracle / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 4 | 1 |
| NE | 0 | 6 | 0 |
| II | 0 | 8 | 8 |


## S2 vs B1 (paired, per run)

| Model | Run | Accuracy diff | McNemar p | FER diff [95% CI] |
|---|---|---|---|---|
| gemini-flash-lite | 0 | -0.257 | 0.0001 | -0.056 [-0.139, +0.000] |
| gpt-oss-20b | 0 | -0.119 | 0.0725 | -0.028 [-0.083, +0.000] |

Holm-adjusted p-values: gemini-flash-lite/run0: 0.0002, gpt-oss-20b/run0: 0.0725

## Accuracy by criterion type (all runs pooled; a missed criterion counts as wrong)

| System | Model | min_grade | years_of_education | min_credits | degree_level | degree_field | age_limit | nationality | english_test | work_experience | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | none | 0.065 (n=62) | 0.077 (n=13) | 0.000 (n=9) | 0.000 (n=84) | 0.000 (n=23) | 0.378 (n=45) | 0.000 (n=77) | 0.089 (n=45) | 0.000 (n=18) | 0.000 (n=18) |
| B1 | gemini-flash | 0.100 (n=10) | 0.333 (n=3) | 0.500 (n=2) | 0.571 (n=14) | 0.750 (n=4) | 0.500 (n=8) | 0.929 (n=14) | 0.222 (n=9) | 1.000 (n=4) | 0.600 (n=5) |
| B1 | gemini-flash-lite | 0.306 (n=62) | 0.154 (n=13) | 0.444 (n=9) | 0.667 (n=84) | 0.565 (n=23) | 0.756 (n=45) | 0.818 (n=77) | 0.333 (n=45) | 0.889 (n=18) | 0.333 (n=18) |
| B1 | gpt-oss-20b | 0.194 (n=62) | 0.462 (n=13) | 0.889 (n=9) | 0.714 (n=84) | 0.348 (n=23) | 0.844 (n=45) | 0.805 (n=77) | 0.311 (n=45) | 0.889 (n=18) | 0.556 (n=18) |
| S2 | gemini-flash-lite | 0.581 (n=62) | 0.077 (n=13) | 0.111 (n=9) | 0.464 (n=84) | 0.565 (n=23) | 0.156 (n=45) | 0.610 (n=77) | 0.600 (n=45) | 0.889 (n=18) | 0.722 (n=18) |
| S2 | gpt-oss-20b | 0.371 (n=62) | 0.154 (n=13) | 0.111 (n=9) | 0.405 (n=84) | 0.435 (n=23) | 0.044 (n=45) | 0.286 (n=77) | 0.778 (n=45) | 0.500 (n=18) | 0.667 (n=18) |
| S2-oracle | gemini-flash-lite | 0.600 (n=5) | 0.000 (n=4) | 0.000 (n=9) | 0.762 (n=21) | 0.500 (n=18) | 1.000 (n=4) | 1.000 (n=4) | 0.900 (n=20) | 1.000 (n=2) | - |
| S2-oracle | gpt-oss-20b | 0.600 (n=5) | 0.000 (n=4) | 0.000 (n=9) | 0.762 (n=21) | 0.611 (n=18) | 1.000 (n=4) | 1.000 (n=4) | 0.900 (n=20) | 1.000 (n=2) | - |

## Model calls by component (uncached calls only)

| Component | Model | Calls | p50 latency (s) | p95 latency (s) | Mean tokens in/out | Failure rate | Retry rate |
|---|---|---|---|---|---|---|---|
| b1 | gemini-flash | 24 | 50.64 | 265.96 | 1247/170 | 25.00% | 0.00% |
| b1 | gemini-flash-lite | 109 | 6.08 | 12.96 | 1574/234 | 0.00% | 0.00% |
| b1 | gpt-oss-20b | 124 | 2.76 | 61.73 | 1485/214 | 12.10% | 4.84% |
| criteria_extract_retrieved | gemini-flash-lite | 17 | 8.48 | 14.65 | 3611/1645 | 0.00% | 47.06% |
| criteria_extract_retrieved | gpt-oss-20b | 32 | 45.78 | 106.33 | 2503/1126 | 12.50% | 40.62% |
| semantic_judge | gemini-flash-lite | 104 | 5.93 | 6.55 | 499/41 | 0.00% | 0.00% |
| semantic_judge | gpt-oss-20b | 164 | 2.43 | 41.64 | 526/66 | 3.05% | 0.00% |

302 failures in run 0 written to failures.csv - group at least 10 by cause and add planned fixes.