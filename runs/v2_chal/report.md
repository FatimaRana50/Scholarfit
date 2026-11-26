# Results: v2_chal

78 pairs, runs per condition: 1

| System | Model | accuracy | macro_f1 | false_eligible_rate | false_not_eligible_rate | under_abstention | risky_under_abstention | over_abstention | p50 latency (s) | p95 latency (s) | cost / pair (USD) | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | gemini-flash-lite | 0.667 | 0.668 | 0.077 | 0.000 | 0.500 | 0.325 | 0.132 | 6.65 | 70.52 | 0.00000 | 0 |
| B1 | gpt-oss-20b | 0.577 | 0.567 | 0.000 | 0.160 | 0.425 | 0.150 | 0.316 | 2.82 | 57.26 | 0.00000 | 0 |
| S1 | gemini-flash-lite | 0.590 | 0.566 | 0.000 | 0.280 | 0.375 | 0.075 | 0.263 | 37.58 | 186.92 | 0.00000 | 0 |
| S1 | gpt-oss-20b | 0.615 | 0.575 | 0.000 | 0.320 | 0.275 | 0.050 | 0.289 | 17.73 | 62.28 | 0.00000 | 0 |
| S2 | gemini-flash-lite | 0.590 | 0.583 | 0.077 | 0.160 | 0.450 | 0.175 | 0.237 | 0.06 | 48.09 | 0.00000 | 0 |
| S2 | gpt-oss-20b | 0.474 | 0.396 | 0.000 | 0.000 | 0.300 | 0.000 | 0.763 | 0.01 | 11.81 | 0.00000 | 0 |
| S2-oracle | gemini-flash-lite | 0.731 | 0.722 | 0.000 | 0.120 | 0.350 | 0.075 | 0.105 | 0.00 | 24.40 | 0.00000 | 0 |
| S2-oracle | gpt-oss-20b | 0.718 | 0.707 | 0.000 | 0.120 | 0.350 | 0.075 | 0.132 | 0.00 | 30.06 | 0.00000 | 0 |

## Confusion matrices (run 0; rows = gold, columns = predicted)

**B1 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 22 | 0 | 3 |
| NE | 1 | 10 | 2 |
| II | 13 | 7 | 20 |

**B1 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 10 | 4 | 11 |
| NE | 0 | 12 | 1 |
| II | 6 | 11 | 23 |

**S1 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 9 | 7 | 9 |
| NE | 0 | 12 | 1 |
| II | 3 | 12 | 25 |

**S1 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 9 | 8 | 8 |
| NE | 0 | 10 | 3 |
| II | 2 | 9 | 29 |

**S2 / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 13 | 4 | 8 |
| NE | 1 | 11 | 1 |
| II | 7 | 11 | 22 |

**S2 / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 4 | 0 | 21 |
| NE | 0 | 5 | 8 |
| II | 0 | 12 | 28 |

**S2-oracle / gemini-flash-lite**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 19 | 3 | 3 |
| NE | 0 | 12 | 1 |
| II | 3 | 11 | 26 |

**S2-oracle / gpt-oss-20b**

| gold \ pred | E | NE | II |
|---|---|---|---|
| E | 19 | 3 | 3 |
| NE | 0 | 11 | 2 |
| II | 3 | 11 | 26 |


## S2 vs B1 (paired, per run)

| Model | Run | Accuracy diff | McNemar p | FER diff [95% CI] |
|---|---|---|---|---|
| gemini-flash-lite | 0 | -0.077 | 0.3771 | +0.000 [-0.231, +0.231] |
| gpt-oss-20b | 0 | -0.103 | 0.2430 | +0.000 [+0.000, +0.000] |

Holm-adjusted p-values: gpt-oss-20b/run0: 0.4860, gemini-flash-lite/run0: 0.4860

## Accuracy by criterion type (all runs pooled; a missed criterion counts as wrong)

| System | Model | min_grade | years_of_education | min_credits | degree_level | degree_field | age_limit | nationality | english_test | work_experience | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | gemini-flash-lite | 0.750 (n=28) | 0.333 (n=6) | 0.857 (n=14) | 0.737 (n=57) | 0.838 (n=37) | 1.000 (n=15) | 0.533 (n=15) | 0.852 (n=54) | 0.250 (n=8) | - |
| B1 | gpt-oss-20b | 0.750 (n=28) | 0.000 (n=6) | 0.929 (n=14) | 0.772 (n=57) | 0.703 (n=37) | 1.000 (n=15) | 0.867 (n=15) | 0.778 (n=54) | 0.875 (n=8) | - |
| S1 | gemini-flash-lite | 0.643 (n=28) | 0.500 (n=6) | 1.000 (n=14) | 0.702 (n=57) | 0.595 (n=37) | 1.000 (n=15) | 0.533 (n=15) | 0.648 (n=54) | 0.750 (n=8) | - |
| S1 | gpt-oss-20b | 0.821 (n=28) | 0.000 (n=6) | 0.929 (n=14) | 0.509 (n=57) | 0.676 (n=37) | 1.000 (n=15) | 0.600 (n=15) | 0.759 (n=54) | 0.375 (n=8) | - |
| S2 | gemini-flash-lite | 0.786 (n=28) | 0.833 (n=6) | 0.286 (n=14) | 0.930 (n=57) | 0.595 (n=37) | 1.000 (n=15) | 0.600 (n=15) | 0.556 (n=54) | 1.000 (n=8) | - |
| S2 | gpt-oss-20b | 0.786 (n=28) | 0.167 (n=6) | 0.286 (n=14) | 0.228 (n=57) | 0.622 (n=37) | 0.133 (n=15) | 0.267 (n=15) | 0.444 (n=54) | 0.250 (n=8) | - |
| S2-oracle | gemini-flash-lite | 0.857 (n=28) | 0.500 (n=6) | 0.000 (n=14) | 0.895 (n=57) | 0.865 (n=37) | 1.000 (n=15) | 0.600 (n=15) | 0.889 (n=54) | 1.000 (n=8) | - |
| S2-oracle | gpt-oss-20b | 0.964 (n=28) | 0.500 (n=6) | 0.000 (n=14) | 0.895 (n=57) | 0.757 (n=37) | 1.000 (n=15) | 0.600 (n=15) | 0.889 (n=54) | 1.000 (n=8) | - |

## Model calls by component (uncached calls only)

| Component | Model | Calls | p50 latency (s) | p95 latency (s) | Mean tokens in/out | Failure rate | Retry rate |
|---|---|---|---|---|---|---|---|
| b1 | gemini-flash-lite | 78 | 6.64 | 70.52 | 1140/201 | 2.56% | 0.00% |
| b1 | gpt-oss-20b | 78 | 2.81 | 57.24 | 1266/213 | 0.00% | 6.41% |
| criteria_extract_retrieved | gemini-flash-lite | 14 | 85.61 | 259.28 | 2821/1490 | 14.29% | 57.14% |
| criteria_extract_retrieved | gpt-oss-20b | 23 | 7.43 | 82.71 | 1460/792 | 39.13% | 17.39% |
| s1_criterion | gemini-flash-lite | 385 | 6.09 | 16.16 | 485/47 | 3.38% | 0.00% |
| s1_criterion | gpt-oss-20b | 335 | 2.46 | 32.03 | 505/63 | 5.97% | 0.00% |
| semantic_judge | gemini-flash-lite | 137 | 6.03 | 15.72 | 490/41 | 0.00% | 0.00% |
| semantic_judge | gpt-oss-20b | 105 | 2.47 | 29.88 | 549/66 | 0.00% | 0.00% |

237 failures in run 0 written to failures.csv - group at least 10 by cause and add planned fixes.