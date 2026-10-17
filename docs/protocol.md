# Scientific protocol v0.1

## Objective

Describe and explain **aggregate** municipal variation in turnout and observed presidential voting between the 2022 and 2026 elections. Quantify uncertainty and test whether added model complexity improves out-of-sample performance.

## Data governance

Only official publicly available aggregate election returns, electorate summaries, and compatible aggregate geographic context. No individual-level voting preferences, political audience segmentation, or persuasion targeting. Preserve source licenses and provenance.

## Stage 1 — Audit and harmonization

Inventory exact official resources, capture retrieval timestamps and SHA256 checksums, inspect official data dictionaries, reconcile totals for the correct office and round. Treat TSE municipality IDs and IBGE municipality IDs as different key systems until crosswalks have been verified. Do not assume that a 2022 section ID matches its 2026 counterpart. The location of a polling station is not a residential neighborhood.

## Stage 2 — Descriptive analysis

Compute turnout, abstention, valid-vote shares and uncertainty-aware differences at a **comparable** spatial scale. Restrict candidate-to-candidate comparisons to explicitly justified cases. Do not interpret shifts in aggregate shares as individual voter transitions.

## Stage 3 — Models

Baseline: weighted mean, regularized regression. Competitors: partial-pooling hierarchical models with optional geographic effects. Register outcome definitions and covariate observation dates before fitting; no post-election predictors in historical forecasting experiments.

## Stage 4 — Validation

Hold out whole municipalities and geographic blocks; where valid, train on earlier elections and evaluate on later elections. Report MAE/RMSE in percentage points, calibration and residual analysis. Compare with simple baselines. No estimates of 2026 second-round outcome until observations exist; do not represent in-sample explanatory fit as genuine forecast skill.

## Stage 5 — Artifacts

Version methodology, schema checks, source manifest, code revision, experiment config, metrics and figures. Report data quality failures, negative findings and model limitations. Never fabricate results.

## Research status

Initialized: **no official electoral dataset has been downloaded or analyzed yet; no model has been fit**.
