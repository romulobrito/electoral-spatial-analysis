# E015 — Official-data sequential reveal experiment: results (26 October 2026)

## Status and provenance

**Reproduced with official aggregate source snapshots; findings are exploratory, not prospective forecasting validation.**

- Reproducible successful [GitHub Actions run 40389373595](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40389373595), Git revision `94b7622ac1e83338e6bc42cfa5e663e21bec19d3`. **93 tests passed**, Ruff clean.
- Output [artifact 12681879043](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40389373595/artifacts/12681879043): `metadata.json`, `path_errors.csv`, `scenario_summary.csv` (14-day GitHub artifact retention).
- Uploaded ZIP SHA256: `196c31a127b9bacc865802926e763dce377b13260c8a86e3136ccb9d0ea78a09`.
- E005 TSE municipal panel SHA256: `2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d`.
- E006 IBGE 2022 Census snapshot SHA256: `145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641`.

**Sample:** 5,569 audited municipalities in 27 UF/DF groups; exclude the previously documented exceptional Amazonas municipality. **Target:** 2026 first-round *aggregate turnout*, final observed 79.12355% in the comparable sample. No candidate-vote totals or presidential victory forecasting. The actual reporting order is not known here: all **245** full-municipality reveal sequences are counterfactual (120 uniform random, 120 state-balanced random, five deterministic). They are not independent elections. Reveal stages refer to the share of **registered electorate in revealed municipalities**, not the fraction of reported ballot boxes or sections.

The study produces 245 × 9 thresholds × 8 models = **17,640 rows**. Each stage contains unchanged E014 reference models (partial share, historical fixed 2022, national swing, UF-shrunk swing) and four E015 online models (E007 linear Ridge ± regional correction; E013 quadratic Ridge ± regional correction). On each stage, fitting and scaling use only revealed municipalities' 2026 turnout. The unseen current outcomes are used only for scoring. Ridge penalty 10 and the macroregional intercept shrinkage 100 were preserved; fallback to national swing occurs when fitting is unsupported.

## MAE by model at 2.5% target coverage (pp)

The random-scenario columns are means across **120 synthetic paths each**. The deterministic scenarios have one path; their values are errors on that one path, not sample averages of independent repetitions.

| Model | Uniform random | UF-balanced random | Low 2022 turnout first | High 2022 turnout first | Small municipalities first | UF blocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical fixed 2022 | 0.095 | 0.095 | 0.095 | 0.095 | 0.095 | 0.095 |
| Partial observed share | 0.848 | 1.257 | 6.330 | 6.254 | 0.452 | 0.403 |
| National observed swing | 0.510 | 0.617 | 4.385 | 1.093 | 0.452 | 1.983 |
| UF-shrunk swing | 0.480 | 0.514 | 4.243 | 1.157 | 0.390 | 1.984 |
| E007 online Ridge | 0.753 | 0.613 | 7.474 | 0.260 | 3.317 | 1.172 |
| E007 online Ridge + macroregion | 0.728 | 0.606 | 7.394 | 0.282 | 3.301 | 1.174 |
| E013 online quadratic Ridge | 0.642 | 0.416 | 1.256 | 6.781 | 0.024 | 1.357 |
| E013 online quadratic Ridge + macroregion | 0.660 | 0.418 | 1.186 | 6.761 | 0.034 | 1.360 |

Note: large-municipality-first gives 2.036 pp for all four E015 variants and the two swing variants at this threshold: the initial revealed sample is too small to train and the E015 estimators fall back to national swing.

## Matched comparisons of quadratic Ridge against the UF-shrunk swing

- At **2.5%** coverage in **UF-balanced random** arrival, E013 quadratic reaches 0.416 pp versus 0.514 pp for UF-shrunk swing, a mean improvement of **0.098 pp**. E013 has lower absolute error on **74 of 120** matched paths.
- At **2.5%** coverage in **uniform random** arrival, E013 quadratic reaches 0.642 pp versus 0.480 pp, a **0.162 pp deterioration**. It wins on **54 of 120** matched paths.
- At **10%** coverage, quadratic Ridge reaches **0.424 vs 0.292 pp** (uniform) and **0.350 vs 0.282 pp** (UF-balanced), again worse than UF-shrunk swing in both averages.
- E007 Ridge + macroregion does not improve the 2.5% or 10% scenario mean relative to UF-shrunk swing in either random regime. Macroregional correction itself does not consistently help.

These comparisons reuse the same orders and thresholds. They provide controlled **within-election sensitivity** observations, not a claim of superior performance across independent elections.

## Failure analysis at the earliest reveal stage

The most extreme error is **61.454 pp** for E013 quadratic Ridge in the **small-municipality-first** sequence at the 0.25% target (actual coverage 0.251276%; 202 municipalities revealed). It estimates national turnout at **17.669%**, versus 79.12355% observed. Its macroregional variant has essentially the same failure (61.454 pp). The unchanged UF-shrunk swing has 0.812 pp error and national swing 0.844 pp in this identical setting.

Additional early failures: high-2022-turnout-first, 0.25% target, quadratic ~18.96 pp absolute error; low-2022-turnout-first, 0.25%, quadratic ~13.86 pp. These are large real weaknesses in the online models, *not* evidence of temporal leakage. They are compatible with extrapolation/out-of-support when highly nonrepresentative municipalities arrive first, but coefficient-level or feature-support diagnostics are required to attribute the mechanism precisely.

The fallback was used for 129 of 245 paths at 0.25% target, and 121 of 245 at 1%. The first stage's extreme errors occurred in paths in which the Ridge fitting was permitted; 10 revealed units is therefore **not** a sufficient stability guarantee.

## Critical interpretation

1. **No robust superiority:** Increasing the complexity from E014 to online E007/E013 estimators did not yield uniform or adversarially robust improvement.
2. **Historical persistence anomaly:** The 2022 fixed-turnout weighted reference is 79.2185%, only ~0.0950 pp from the 2026 observed rate. This explains its unusually low constant error; a single election provides no basis to expect the same result in a future election.
3. **Adversarial risk:** The quadratic models can extrapolate badly from narrow early samples, despite the absence of hidden-target training information.
4. **No true temporal holdout:** Training during simulated reveals uses *partially observed 2026* targets. This is valid for the artificial reveal experiment, but does not validate a future election independent of 2026.
5. **No predictive interval calibration:** No claims of 95% coverage, probability of victory or sufficient completeness of ballot-box reporting may be drawn.
6. **Spatial E008–E010:** Geographic Moran diagnostics remain separate from the estimators; significance of residual spatial autocorrelation in previous studies does not establish prospective improvement here.

## Recommended next experiment (E016, explicitly exploratory)

Freeze E015 unchanged as the adverse-case benchmark. Investigate train-only stability controls: minimum effective sample size and UF coverage; observed-covariate support diagnostics; robust/clamped **predicted turnout change** rather than only final probability; and shrinkage to 2022 persistence or UF-smoothed swing. Evaluate these against the same frozen paths **as a development set**, and reserve independent elections and/or previously unexamined reveal patterns for confirmation. Avoid choosing a model on the current 2026 data and then reporting the resulting 2026 gain as independent confirmation. Persist diagnostics for each predicted stage (revealed units, UF coverage, extrapolation and fallback reason).

**Decision:** Keep PR #21 as an experimental method/result record; do not promote the E013 online quadratic estimator to a production early-projection component.

### Reproduce

```bash
python -m electoral_analysis.arrival_model_integration \
  --panel outputs/e005-results/municipal_results.json \
  --census data/reference/ibge_4714_2022.json \
  --out-dir outputs/e015 \
  --reps 120 --seed 20261026
```

The output directory must not exist before the run. Recovery of official E005/E006 inputs is implemented in `.github/workflows/e015-online-models.yml`.
