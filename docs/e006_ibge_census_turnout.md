# E006 — IBGE Census 2022 and aggregate municipal turnout

## Goal

Evaluate whether resident population and population density of municipalities can help **describe retrospective changes in first-round turnout**, compared with persistence of observed 2022 turnout. This does not model candidate choice, future political support, campaign opportunity or individual voting preference.

## Sources and ETL

- Official IBGE 2022 Census `agregado=4714`, variables `93` resident population, `6318` area in km² and `614` population density per km²; 2022 period, municipality `N6`. Official API URL is fixed in `src/electoral_analysis/ibge_turnout.py`.
- Official TSE national 2022/2026 election archives were reconciled in E005. Use E005's previously audited artifact from Actions run `39069589159`, verifying its 2022 and 2026 source hashes and 5,570 paired municipalities.
- Exact municipality crosswalk is official TSE–IBGE ZIP generated October 11, 2026, with SHA256 `68328ddc166806594a2aab5809ac9aa602153535d6b8a71e886c337f9f3631ca`.

Reject unrecognized IBGE indicators, years, municipality keys, duplicate series or invalid numeric values. Preserve original Census response and SHA256 manifest. Missing values are excluded only with explicit quality counts; none are silently imputed. Flag and exclude the affected Amazonas municipality (2022 TSE ID 2550, 84 exceptional electors) from model evaluation until its 2022 denominator is certified.

## Pre-registered statistical comparison

**Baseline:** carry forward 2022 first-round municipal turnout rate, assuming 0 percentage-point change.

**Comparator:** ridge regression on 2026 minus 2022 turnout (percentage points). Inputs are 2022 turnout rate, log(1 + Census 2022 population) and log(1 + Census 2022 density). Ridge penalty fixed at 10, no post-hoc hyperparameter search; standardize using training municipalities only.

**Validation:** leave-one-state-out. Hold out one entire state, fit on the others, evaluate exclusively in held-out state, repeat across all states. Report pooled absolute-error MAE and RMSE in percentage points, as well as the signed model-minus-baseline MAE difference. Bootstrap state clusters (400 replicates, fixed seed 2718) to provide a *descriptive* sensitivity interval around the difference in MAE. Diagnostic state folds are alphabetically ordered, not ranked by electoral value.

**Limitations:** This is retrospective, not a demonstrated ex-ante 2022 forecast (Census 2022 release timing matters). Predictive associations are not causal and do not identify individual participation motives. The available voting-section location does not identify a voter's residential neighborhood. Candidate choices, support scores and persuasion effectiveness are outside the analysis.

**Reproducibility:** `.github/workflows/e006-census-turnout.yml` obtains the signed E005 artifact (which expires; rerun E005 if necessary), the official crosswalk and IBGE source, runs tests/lint and emits a summarized JSON report. Do not commit raw bulk data or unvalidated results.
