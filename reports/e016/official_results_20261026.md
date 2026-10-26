# E016 — Retrospective robustness with audited first-round turnout (2026-10-26)

## Execution and provenance

Successful complete official-source experiment: [GitHub Actions run 40394615650](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40394615650). Audited E005 2022/2026 TSE turnout panel and E006 2022 IBGE Census artifacts were retrieved by the workflow and verified in the E015/E016 loaders. Output [artifact 12685443528](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40394615650/artifacts/12685443528), archive SHA256 `b3b4495184180494e60c3babbf797b1dcc3bbe83de001a513da14335dbbc7b68`.

The complete experiment covers **5,569 municipalities, 245 counterfactual reveal permutations, nine electorate-coverage stages, ten models, and 22,050 model×path×stage records.** Tests and lint succeeded. This is **not** an actual election-night sequence nor second-round candidate-share forecasting.

E016 adds a gated E007 linear and E013 quadratic model to the unchanged eight E014/E015 estimators. When coverage, weighted effective sample size, or train-derived covariate-support tests fail, E016 uses the unchanged E014 UF-shrunk swing. Other scenarios use train-derived clipped turnout changes and novelty-dependent blending with that reference. **All 2026 hidden municipality turnout is excluded from fitting, preprocessing, gating and blending; the known final outcome is consulted for retrospective scoring only.**

## Matched mean absolute errors, 2.5% electorate coverage (percentage points)

| Method | Uniform random (120) | UF-balanced random (120) |
|---|---:|---:|
| Fixed historical 2022 | 0.095 | 0.095 |
| E014 UF-shrunk swing | 0.480 | 0.514 |
| E015 E007 Ridge + region | 0.728 | 0.606 |
| E015 E013 quadratic | 0.642 | 0.416 |
| E016 guarded linear | 0.485 | 0.514 |
| E016 guarded quadratic | 0.477 | 0.514 |

At this 2.5% stage the guarded models **fell back on 116/120 uniform paths and 120/120 UF-balanced paths**. Thus their near-baseline scores are mostly a consequence of conservative fallback, **not evidence that guarded E007/E013 regression is accurate when active**. At 0.25% and 1% coverage, fallback occurs in **all** 245 paths for both E016 methods.

## Worst-case robustness

Maximum absolute error across all path/coverage pairs:
- E015 quadratic: **61.454 pp** (smallest municipalities first at 0.25% electorate coverage).
- E016 guarded linear and quadratic: **4.248 pp** (low-historical-turnout municipalities first at 1% coverage, falling back to E014 UF swing).
- E014 UF swing: **4.248 pp**; fixed historical 2022 **0.095 pp** (unusually accurate for this one observed election).

The 61.454-pp E015 failure is prevented by the E016 abstention-from-fit/fallback mechanism, not by proving valid quadratic extrapolation. At 10% stage, fallback still occurs for **91.4%** of sequences; at 25%, **91.0%**; at 50%, **63.3%**. The gates are deliberately restrictive, often overriding useful regression information along with unsafe regression. Independent prospective validation and sensitivity to threshold choice are required.

## Status and decision

E016 successfully stabilizes the worst retrospective extrapolation through conservative abstention, but does **not** demonstrate consistently superior predictive accuracy over UF-shrunk swing or the remarkably accurate fixed 2022 national reference. The revealed 2026 municipalities are training data, but all paths evaluate the *same election*, not independent temporal holdouts. These thresholds were designed after E015 failure was observed, so the comparison is exploratory. There is no validated 95% forecast interval, section-level chronology, individual-level preference inference or candidate-specific projection.

Keep E015 and E016 separate and do not promote the guarded estimator as a validated production improvement. An E017 could study alternative pre-specified gate thresholds on a development split of arrival patterns, with *held-out pattern families* and, when available, independent future election data. Report active-fit-only metrics alongside fallback-dominant metrics and relative performance against untouched baselines.

Run: `python -m electoral_analysis.arrival_robustness --panel outputs/e005-results/municipal_results.json --census data/reference/ibge_4714_2022.json --out-dir outputs/e016 --reps 120 --seed 20261026`.
