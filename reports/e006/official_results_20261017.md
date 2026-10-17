# E006 — Official IBGE Census 2022 and state-heldout municipal turnout evaluation

**Execution date:** 2026-10-17. **Status:** Full official-data workflow passed, all 27 state holdouts evaluated, source and quality checks recorded.

## Objective and scope

Test whether aggregate resident population and demographic density from Census 2022 add retrospective explanatory/predictive value for **municipal first-round turnout changes between 2022 and 2026**, compared with historical turnout persistence. Neither the model nor the report estimates candidate preferences, Lula's future vote totals, persuasion potential, or personal/household political attributes.

## Reproducibility

- Full [GitHub Actions run 39072126444](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39072126444): **success**.
- [Machine-readable state holdout metrics and original IBGE JSON snapshot](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39072126444/artifacts/12115327463) (14-day retention). The raw official municipal election E005 panel is retained in its prior artifact for reproduction.
- [IBGE official Census API](https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93%7C6318%7C614?localidades=N6%5Ball%5D): aggregate 4714, population (93), area (6318), demographic density (614); year 2022; geographical level N6.
- Decoded IBGE JSON SHA256: `145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641`.
- E005 electoral panel SHA256: `2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d`. The underlying official election ZIP hashes and TSE–IBGE crosswalk were separately checked during ingestion.

## Quality gates

| Test | Outcome |
| --- | ---: |
| Census 2022 municipalities with all three variables | 5,570 |
| Election panel paired municipalities | 5,570 |
| Exact IBGE matches | **5,570** |
| Municipalities unmatched in official IBGE series | **0** |
| Exception flags, AM municipality IBGE 1302603 | **1** |
| Valid independent held-out municipalities | **5,569** |
| Entire-state holdout folds (UFs incl. DF) | **27** |

Municipality IBGE **1302603** is excluded from statistical validation pending municipality-specific reconciliation of the 2022 exceptional 84-eligible-elector section. It is not removed from the underlying audited election panel.

## Pre-registered evaluation

For each state, train on the other 26 units and evaluate on the held-out state. The target is **2026 minus 2022 aggregate turnout in percentage points**. Baseline predicts zero turnout change (carry forward the 2022 turnout rate). Comparator is a three-feature ridge model trained on previous turnout rate, log1p(2022 municipal Census population), log1p(2022 density), with penalty **10** fixed in advance and training-fold-only normalization.

| Metric (percentage points) | Persistence baseline | Fixed ridge, 27 state holdouts |
| --- | ---: | ---: |
| **Pooled MAE** | 2.1355 | **1.9567** |
| **Pooled RMSE** | 2.8577 | **2.5024** |

Pooled ridge MAE is **0.1788 percentage points lower** than the persistence baseline (an ~8.37% relative decrease in MAE); no candidate vote outcome is involved.

### Robustness and uncertainty

- Across 27 state holdout folds, ridge has lower MAE in **17**, and greater MAE in **10**. These are diagnostics rather than a ranking of states by any electoral value.
- A reproducible state-cluster bootstrap (400 draws, seed 2718) for **ridge-minus-baseline MAE** produces a percentile interval of **[−0.4687, +0.0904] percentage points**.
- The interval crosses **zero**: the observed pooled average gain is **not established as robustly positive across resampled state populations**. A more complex model therefore cannot yet be claimed reliably superior to the persistence baseline. This is a meaningful negative/inconclusive scientific finding and should be retained.

## Limitations and next stages

1. All features come from census reference year 2022, but their public release timing may differ; the evaluation is **retrospective**, not a demonstrated operational 2022 ex-ante forecast.
2. Leave-state-out evaluation tests spatial transportability. It does not establish causal mechanisms; residual spatial dependence and state composition require examination.
3. Demographic variables may correlate with turnout through confounding and registration changes; neither correlations nor coefficients identify individual behaviors.
4. Municipal precinct data cannot be assigned directly to residential neighborhoods. Neighborhood analyses require distinct data with verified residential geography.
5. Resulting analyses do not provide political preference profiles, candidate-electability scores, or geographic persuasion recommendations.

## Files

- `src/electoral_analysis/ibge_turnout.py`: official-data ingestion, quality gates and model.
- `tests/test_ibge_turnout.py`: schema, duplicate, exception and holdout tests.
- `.github/workflows/e006-census-turnout.yml`: full reproducible workflow.
- `docs/e006_ibge_census_turnout.md`: scientific protocol and sources.

**Conclusion:** Municipality population and density supplied a modest, observable improvement in this retrospective leave-state-out comparison, but the clustered uncertainty interval includes no gain. Further independent robustness studies are needed before asserting a dependable enhancement in turnout modeling.
