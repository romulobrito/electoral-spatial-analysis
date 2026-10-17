# E007 — Explanatory residual study of municipal turnout

## Scientific question

The E006 fixed ridge reduced retrospective first-round municipal turnout MAE compared with simple persistence, yet the state-cluster bootstrap interval crossed zero. E007 investigates **systematic signed residuals** and whether a strictly train-only macrorregional intercept adjustment changes aggregate turnout error under leave-one-state-out testing.

This is NOT a candidate-choice model or a tool to identify persuasive political audiences. No political-preference score or neighborhood inference is computed.

## Prediction and partition

For each of the 27 state/DF heldout folds, use exactly the E006 covariates:
2022 municipal turnout, log1p(Census 2022 population) and log1p(2022 density). Fit ridge of the 2026 minus 2022 turnout percentage-point change with ridge penalty 10 and train-fold-only standardization. The heldout state's observations do not influence coefficients, scaling, regional correction or choices.

For each macrorregion, compute the **training residual mean** using all other states of that same macrorregion. Apply an intercept adjustment equal to residual sum / (training count + 100). Shrinkage hyperparameter 100 is fixed before E007 execution and **was not** tuned on heldout states; however, the method itself was chosen after seeing E006 results, thus results remain exploratory and require independent validation on a future election.

## Analyses

Report overall MAE/RMSE of persistence, ridge and ridge + macrorregion; signed residual bias and MAE by five macrorregions; state-alphabetical fold results and global tercile diagnostics for population and density. State labels are diagnostic, not recommendation or targeting priority. Report share of signed residual variance accounted for by state means (eta squared). Do NOT claim this is Moran's I; actual adjacency would require compatible shapefiles and an explicitly defined spatial weight matrix.

Use 400 state-cluster bootstrap replicates (fixed seed 2718) for sensitivity intervals of model-minus-baseline errors; they are exploratory confidence/sensitivity indications, not causal effects or independent confirmatory tests.

## Inputs, exclusions and provenance

Use unchanged, checksum-verified E005 municipality panel and E006 2022 Census snapshot, with one Amazonas exceptional 2022 municipality excluded from model comparisons (IBGE code 1302603). The municipality crosswalk must match independently established SHA256. Reproduce from `.github/workflows/e007-residual-analysis.yml` and keep the JSON and SVG as CI artifacts. Neither registered electorate nor voting returns are inferred at personal or residential-neighborhood levels.
