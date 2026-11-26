# Results: v2_main

109 pairs, runs per condition: 1

| System | Model | accuracy | macro_f1 | false_eligible_rate | false_not_eligible_rate | under_abstention | risky_under_abstention | over_abstention | p50 latency (s) | p95 latency (s) | cost / pair (USD) | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | gemini-flash-lite | 0.651 | 0.606 | 0.056 | 0.000 | 0.450 | 0.183 | 0.184 | 0.02 | 0.02 | 0.00000 | 0 |
| B1 | gpt-oss-20b | 0.569 | 0.527 | 0.028 | 0.462 | 0.533 | 0.100 | 0.163 | 0.02 | 0.03 | 0.00000 | 0 |
| S1 | gemini-flash-lite | 0.541 | 0.574 | 0.000 | 0.077 | 0.750 | 0.017 | 0.082 | 36.39 | 72.68 | 0.00000 | 0 |
| S1 | gpt-oss-20b | 0.477 | 0.363 | 0.000 | 0.692 | 0.750 | 0.050 | 0.061 | 45.84 | 126.07 | 0.00000 | 0 |
| S2 | gemini-flash-lite | 0.606 | 0.566 | 0.000 | 0.077 | 0.383 | 0.000 | 0.388 | 0.05 | 12.83 | 0.00000 | 0 |
| S2 | gpt-oss-20b | 0.560 | 0.429 | 0.000 | 0.385 | 0.333 | 0.000 | 0.469 | 0.03 | 5.86 | 0.00000 | 0 |
| S2-oracle | gemini-flash-lite | 0.500 | 0.450 | 0.000 | 0.667 | 0.562 | 0.000 | 0.083 | 0.02 | 0.08 | 0.00000 | 0 |
| S2-oracle | gpt-oss-20b | 0.536 | 0.475 | 0.000 | 0.667 | 0.500 | 0.000 | 0.083 | 0.02 | 0.05 | 0.00000 | 0 |

## Confusion matrices (run 0; rows = gold, columns = predicted)

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

**S1 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 8 | 1 | 4 |
| NE | 0 | 36 | 0 |
| II | 1 | 44 | 15 |

**S1 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 9 | 3 |
| NE | 0 | 36 | 0 |
| II | 3 | 42 | 15 |

**S2 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 4 | 1 | 8 |
| NE | 0 | 25 | 11 |
| II | 0 | 23 | 37 |

**S2 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 1 | 5 | 7 |
| NE | 0 | 20 | 16 |
| II | 0 | 20 | 40 |

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
| gemini-flash-lite | 0 | -0.046 | 0.5601 | -0.056 [-0.139, +0.000] |
| gpt-oss-20b | 0 | -0.009 | 1.0000 | -0.028 [-0.083, +0.000] |

Holm-adjusted p-values: gemini-flash-lite/run0: 1.0000, gpt-oss-20b/run0: 1.0000

## Accuracy by criterion type (all runs pooled; a missed criterion counts as wrong)

| System | Model | min_grade | years_of_education | min_credits | degree_level | degree_field | age_limit | nationality | english_test | work_experience | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | gemini-flash-lite | 0.306 (n=62) | 0.154 (n=13) | 0.444 (n=9) | 0.667 (n=84) | 0.565 (n=23) | 0.756 (n=45) | 0.818 (n=77) | 0.333 (n=45) | 0.889 (n=18) | 0.333 (n=18) |
| B1 | gpt-oss-20b | 0.194 (n=62) | 0.462 (n=13) | 0.889 (n=9) | 0.714 (n=84) | 0.348 (n=23) | 0.844 (n=45) | 0.805 (n=77) | 0.311 (n=45) | 0.889 (n=18) | 0.556 (n=18) |
| S1 | gemini-flash-lite | 0.323 (n=62) | 0.769 (n=13) | 0.333 (n=9) | 0.702 (n=84) | 0.478 (n=23) | 0.533 (n=45) | 0.506 (n=77) | 0.333 (n=45) | 0.778 (n=18) | 0.722 (n=18) |
| S1 | gpt-oss-20b | 0.226 (n=62) | 0.000 (n=13) | 1.000 (n=9) | 0.298 (n=84) | 0.391 (n=23) | 0.689 (n=45) | 0.610 (n=77) | 0.444 (n=45) | 0.889 (n=18) | 0.333 (n=18) |
| S2 | gemini-flash-lite | 0.581 (n=62) | 0.923 (n=13) | 0.111 (n=9) | 0.512 (n=84) | 0.478 (n=23) | 0.156 (n=45) | 0.779 (n=77) | 0.578 (n=45) | 0.889 (n=18) | 0.722 (n=18) |
| S2 | gpt-oss-20b | 0.435 (n=62) | 0.154 (n=13) | 0.111 (n=9) | 0.310 (n=84) | 0.261 (n=23) | 0.067 (n=45) | 0.208 (n=77) | 0.733 (n=45) | 0.722 (n=18) | 0.333 (n=18) |
| S2-oracle | gemini-flash-lite | 0.600 (n=5) | 0.000 (n=4) | 0.000 (n=9) | 0.762 (n=21) | 0.500 (n=18) | 1.000 (n=4) | 1.000 (n=4) | 0.900 (n=20) | 1.000 (n=2) | - |
| S2-oracle | gpt-oss-20b | 0.600 (n=5) | 0.000 (n=4) | 0.000 (n=9) | 0.762 (n=21) | 0.611 (n=18) | 1.000 (n=4) | 1.000 (n=4) | 0.900 (n=20) | 1.000 (n=2) | - |

## Model calls by component (uncached calls only)

| Component | Model | Calls | p50 latency (s) | p95 latency (s) | Mean tokens in/out | Failure rate | Retry rate |
|---|---|---|---|---|---|---|---|
| criteria_extract_retrieved | gemini-flash-lite | 24 | 9.94 | 253.10 | 2556/1597 | 29.17% | 20.83% |
| criteria_extract_retrieved | gpt-oss-20b | 18 | 50.33 | 111.26 | 3533/1716 | 5.56% | 44.44% |
| s1_criterion | gemini-flash-lite | 817 | 6.01 | 9.43 | 390/43 | 17.87% | 0.00% |
| s1_criterion | gpt-oss-20b | 821 | 2.42 | 35.01 | 420/62 | 16.44% | 0.00% |
| semantic_judge | gemini-flash-lite | 76 | 6.02 | 9.27 | 491/43 | 0.00% | 0.00% |
| semantic_judge | gpt-oss-20b | 77 | 2.36 | 11.15 | 275/39 | 49.35% | 0.00% |

310 failures in run 0 written to failures.csv - group at least 10 by cause and add planned fixes.