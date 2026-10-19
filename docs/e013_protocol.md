# E013 — Multivariate and nonlinear models of **aggregate municipal turnout**

## Question and pre-specified protocol

The preceding bivariate Census chart had weak association (Rio de Janeiro density–turnout Pearson r about −0.168). A low bivariate correlation does not exclude conditional associations or nonlinear predictive structure. E013 separately examines:

1. Descriptive multivariate OLS for 2026 minus 2022 municipal turnout (percentage points) using 2022 turnout, log1p(Census 2022 population), and log1p(Census 2022 density), each standardized, plus 26 **UF fixed-effect** dummies. Report coefficients per 1-SD, cluster-robust standard errors and exploratory 95% CIs grouped by 27 UFs, marginal *sample partial R²*, total in-sample R² and within-UF R². These descriptive coefficients are **not causal** and are not an unseen-state model.
2. Retrospective **27-fold leave-one-UF-out** predictive comparison of existing fixed-alpha=10 E006 ridge, E007 ridge with train-only macroregional intercept, quadratic ridge (squares of three standardized 2022 predictors) and quadratic ridge + a separately trained macroregional intercept. All scaling and intercept corrections must be fit on training UFs only. Preserve official E007 MAE 1.7914991430214526 (pp) exactly within 1e−8 as fail-closed benchmark.
3. Compare new models to E007 using held-out MAE/RMSE and 400 UF-block bootstrap repetitions (seed 2718), with no selection of the lowest apparent error as an independent confirmed discovery.
4. For E007 and quadratic-regional error maps, compute **Moran's I conditional on UF** using original, unsimplified 2022 IBGE queen adjacency restricted to same-UF neighbors and 499 within-UF permutations (seed 2718). This diagnoses residual spatial organization, not a causal spatial process or individual voting behavior.

## Sources and constraints

- Same SHA256-fixed E005 TSE 2022/2026 municipality turnout panel, verified E006 IBGE Census 2022 snapshot and official 2022 municipality boundaries.
- Same **5,569 comparable municipalities** as E006–E010; the previously audited exceptional Amazonas municipality is excluded only from the model comparison.
- Only observed **2022** inputs as predictors. Regression target uses retrospective aggregate 2026 minus 2022 turnout; no candidate-vote targets, personal information, or geography-based persuasion rankings.
- Census 2022 publication dates limit claims of a true 2022 ex-ante prospective forecast. The quadratic basis is an exploratory hypothesis prompted by results of E009/E010, so independent temporal validation is still needed.
- The spatial Moran model uses a geography-conditional null. Significant residual Moran can reflect omitted, spatially patterned variables without a specific causal mechanism.

## Acceptance criteria

Tests cover train-only normalization and exclusion of held-out 2026 outcomes, fixed random seed UF-resampling, official hashes, exact sample and E007 MAE, and reproducibility of the official-dataset workflow. Publish output JSON only after the complete GitHub Actions run succeeds; do not fabricate findings. An atlas scientific chart may be added after validation, without replacing the official source calculations.
