# E010 — Model with historical spatial features for aggregated turnout

**Research question:** Does a spatially lagged **2022 municipal turnout indicator**, computed from official 2022 IBGE topology and 2022 observed election turnout, improve retrospective 2026 municipal turnout prediction out of state over E006 ridge and E007 train-only regional correction? This study is strictly about historical aggregate **participation**, not about any candidate's votes, likelihood of support, electoral potential or persuasion.

## Pre-specified design (frozen before official-data execution)

Datasets: E005 TSE 2022/2026 turnout municipality panel; E006 IBGE 2022 population/density; IBGE 2022 municipal boundary ZIP, all fixed by SHA256. The E005 panel already includes the E004 TSE–IBGE municipality crosswalk and is frozen; never join using a newer mutable crosswalk. Filter only the 2022 Amazonas denominator-exception municipality (IBGE 1302603) from the model evaluation. Main sample: 5,569 municipalities.

### Spatial features and missing-contiguity policy

Build the full domestic sample queen and rook edges from the original unsimplified 2022 IBGE polygons, using *only* geographies and observed first-round **2022** municipal turnout rates. Do **not** compute a neighbor mean from **2026** turnout, target change, candidate votes, held-out 2026 residuals or any outcome known only in the test year.

For each municipality m, `lag_T22_m = mean(T22_n : n shares an edge with m)`. In cases without any graph neighbor, use the municipality's own `T22_m` and explicitly audit the isolate codes/count. Note: computing training-row predictors from neighboring municipalities' **2022** rates, including those geographically in the held-out state, is valid for a retrospective historical-covariate design, because the rates are known before the **2026** target. It would not be permissible to use the held-out state's **2026** results. This validation is retrospective rather than a provably executable pre-2022 forecast, because some Census 2022 indicators were released after the 2022 polling date.

### Models and evaluation

| Model | Outcome | Inputs |
| --- | --- | --- |
| Persistence | First-round 2026 minus 2022 turnout, pp | Predict zero change |
| E006 ridge | Same | 2022 turnout, log1p(Census population), log1p(density) |
| E007 ridge + region | Same | E006 prediction plus train-only macrorregional residual intercept (shrinkage K=100) |
| E010 queen ridge | Same | E006 inputs + **historical queen neighbor turnout 2022** |
| E010 rook ridge | Same | E006 inputs + **historical rook neighbor turnout 2022** |

All ridge fits use fixed penalty **10**; standardization (means, scales) estimated **only on training municipalities** in each of the 27 leave-one-state-out folds. No tuning on held-out 2026 data. Compare MAE and RMSE of all five models over exactly the same sample. Report candidate-minus-E007 MAE and **400 state-cluster bootstrap** replicates with seed **2718**, using pooled MAE differences. Report separate queen and rook models as a **sensitivity study**, not select post hoc the best one as a new confirmed method.

### Residual diagnostics

For each graph, use the E009 definition of conditional within-UF Moran: graph restricted to same-UF neighbors, state-centered residuals, 499 within-UF permutations, seed 2718. Compare E007 ordinary/regional ridge with each E010 spatial-lag model. The historical spatial feature is a predictor: no 2026 turnout outcome or residual lag is used at model fitting or prediction time.

### Acceptance and limitations

The script must reproduce E006 and E007 MAE to tolerance `1e-8`; fail closed if the source hashes, sample membership, graph or historical feature values change. Unit tests demonstrate that modifying an evaluation municipality's 2026 outcome cannot change its own or any training-row spatial feature, and that the fitted ridge excludes held-out targets.

The experiment is **exploratory** because E010 was designed in response to observed E009 spatial residual results. It does not establish prospective predictive performance on unseen election years, explain individual behavior, identify causality, or quantify candidate preference in municipalities/neighborhoods. Source geometry and aggregate test results are persisted by provenance; large raw ZIPs remain external.
