# E005 — Observed municipal presidential votes and turnout baseline (2026-10-17)

## Evidence and provenance

The complete national **first-round** presidential vote archives and section-turnout archives for 2022 and 2026 were re-downloaded and processed in [GitHub Actions run 39069589159](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39069589159). The run passed.

Full aggregate municipality JSON, manifest files and a compact machine-readable summary are retained as [GitHub Actions artifact 12114821473](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39069589159/artifacts/12114821473). These workflow artifacts have a finite retention period; no raw ZIPs are committed to Git.

Official TSE source listings:
- 2022: https://dadosabertos.tse.jus.br/dataset/resultados-2022
- 2026: https://dadosabertos.tse.jus.br/dataset/resultados-2026
- Municipality crosswalk: https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip

The national vote ZIPs and TSE–IBGE crosswalk were **SHA256-pinned** to the snapshots already audited in E002/E004.

## Empirical data-integrity checks

| Election | Category | National votes | Difference from audited benchmark |
| --- | --- | ---: | ---: |
| 2022, first round | Valid | 118,229,719 | 0 |
| 2022, first round | Blank | 1,964,779 | 0 |
| 2022, first round | Null | 3,487,874 | 0 |
| 2026, first round | Valid | 119,306,034 | 0 |
| 2026, first round | Blank | 2,300,798 | 0 |
| 2026, first round | Null | 3,669,003 | 0 |

All six checks passed. The independently computed **municipality-level ballot totals equaled detailed-section attendance** for every retained paired municipality.

The two first-round datasets provided **5,570 matched Brazilian municipalities** using the verified official TSE–IBGE crosswalk, zero 2022-only, and one 2026-only municipality (not imputed with invented 2022 data). Municipal observations contain all candidates, not a shortlist or rank for campaign targeting.

## Turnout persistence baseline

Define for municipal aggregate \(m\):
\[
\widehat{T}_{m,2026} = T_{m,2022}.
\]
Compare with the observed 2026 first-round turnout and report absolute errors in percentage points.

| Metric | Observed |
| --- | ---: |
| Matched municipalities | 5,570 |
| Unweighted MAE | **2.1355 pp** |
| RMSE | **2.8575 pp** |
| MAE weighted by minimum eligible electorate | **1.8973 pp** |
| Unweighted mean municipal change | **+0.5533 pp** |

This is an **outcome-time holdout baseline in retrospect**, not a fitted statistical model. The data have not yet undergone geographic-blocked test splits, and the errors above are about turnout, **not candidate votes or political intent**.

## Scientific interpretation and limits

The workflow now supports **retrospective descriptive comparisons** of municipal first-round votes for all candidacies, using voting shares among **valid votes**. These shares quantify election returns at the geographic aggregate level, not the probability an individual supports a candidate, the votes available to be persuaded, or an estimate of future electoral outcomes.

The 2022 exceptional Amazonas section with 84 eligible electors is part of nationally reconciled electorate but is not yet allocated to the municipality's regular-denominator turnout fraction. This affects a small local subset, so those local denominator statistics remain provisional. In addition, a polling station is not a reliable representation of the electors' residential neighborhood; any neighborhood-level voting inference would require a distinct, documented data source and linkage design.

Future work may add spatially blocked validation for **neutral aggregate turnout models**, compare simple statistical baselines, quantify uncertainty and construct a public civic-information atlas without political-audience scores or customized persuasive recommendations.

## Software tests

Unit tests and Ruff passed in GitHub CI for commit `719d5ff`. The full-data workflow also passed its own test and style gates before computing the reports.
