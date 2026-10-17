# E008 — Global spatial autocorrelation of observed municipal turnout errors

## Objective and previously frozen inputs

Use the official 2022 IBGE municipality digital boundaries to measure **global Moran's I** for retrospectively evaluated turnout errors for 2026 vs. 2022. This study is not an inference of candidate preferences, not a map of political persuasion opportunities and not a residential-neighborhood analysis.

Inputs are fixed by SHA256:
- IBGE 2022 National Municipal Shapefile, EPSG:4674, 5,572 geometries; source `BR_Municipios_2022.zip`.
- E005 aggregate election first-round turnout municipal panel (5,570 comparable domestic municipal identifiers).
- E006 Census 2022 municipal population/density snapshot.
- TSE municipality/IBGE municipality ID crosswalk.
- E007 reference MAE from 27 leave-state-out validations, which must be reproduced exactly.

### Geography compatibility

Of 5,572 polygons, two are operational state areas (Lagoa dos Patos and Lagoa Mirim, Rio Grande do Sul), not the normal election-municipality units; one additional polygon corresponds to the 2022 Amazonas denominator-exception municipality (IBGE 1302603), excluded only from model diagnostics. The model uses **5,569** municipal polygons and must fail if a shape or key is unexpectedly missing. See the [IBGE 2022 mesh publication](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html?edicao=36516&t=acesso-ao-produto).

## Graphs and global Moran

Use the original national 2022 polygon boundaries **without simplification**, touching neighbors (`queen`) and segments of positive shared border (`rook`). Form one symmetric undirected graph per definition, with no self-edges. Edge weights are row-normalized so a municipality's neighbors sum to one. Island municipalities with zero contiguity are **explicitly excluded** from the Moran calculation, not imputed. Compare the set/count of islands across graphs.

For residuals \(e\), calculate

\[
I = \frac{\sum_i \sum_j w_{ij} (e_i - \bar e)(e_j-\bar e)}
{\sum_i(e_i-\bar e)^2}
\]

on connected (non-isolated) nodes; row weights satisfy \(\sum_j w_{ij}=1\). Report expected randomization null \(-1/(N-1)\). For each of baseline, ridge, and ridge-plus-regional error vectors, calculate Moran under both spatial graphs. 499 random permutations with fixed seed 2718 provide approximate, two-sided permutation tails relative to the expectation, plus empirical null quantiles. Six related tests are **exploratory**; no family-wise correction is claimed.

All residuals must be derived from **held-out state predictions**. Do not compute residuals by training and evaluating on the same state.

## Scientific caution

This is a *spatial residual diagnostic*; even a small permutation p-value indicates spatial dependence in this snapshot, **not** geography causing voting behavior, candidate support or individual political traits. Contiguity is not a residential-neighborhood adjacency at the voter level. No candidate-targeting score is constructed, and no outcome pertaining to candidate choice is modeled. The E007 regional correction was selected post hoc and remains exploratory until an independent election confirms it.

## Reproducibility and reporting

Workflow: `.github/workflows/e008-moran.yml`, using GitHub Actions artifacts from the existing E005/E006 runs and hash-pinned official IBGE archive. Emit a compact JSON report and vector SVG into short-lived workflow artifacts; commit verified tables, methods and audit conclusions to `reports/e008/`. Re-run E005/E006 if their artifacts have expired rather than silently using different source snapshots.
