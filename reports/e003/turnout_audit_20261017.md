# E003 — Official turnout reconciliation and provisional municipal comparison

**Data access:** 2026-10-17. **Status:** national electorate, turnout denominator and ballot counts reconciled successfully; **municipal historical crosswalk remains provisional**.

## Evidence

- Complete 2022/2026 detailed voting-section ZIPs processed in [GitHub Actions run 39050102512](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39050102512).
- Independent aggregate vote tally from E002 compared with section turnout.
- CSV and JSON audit artifacts stored with the Actions run (short retention); raw archives not committed.
- Python checks: `src/electoral_analysis/reconcile.py` and `tests/test_reconcile.py`; successful CI.

## National results — reconciled

| Election | Official/effective eligible | Attended | Implied abstention | Turnout |
|---|---:|---:|---:|---:|
| 2022 1st round | 156,454,011 | 123,682,372 | 32,771,639 | 79.0535% |
| 2022 2nd round | 156,454,011 | 124,252,796 | 32,201,215 | 79.4181% |
| 2026 1st round | 158,745,463 | 125,275,835 | 33,469,628 | 78.9162% |

The national first-round turnout rate declined by **0.1373 percentage points** (2026 minus 2022). This is a descriptive, reconciled aggregate difference, **not a prediction or causal effect**.

## Exceptional records and official electorate denominators

The section-detail ZIP includes some presidential rows where `QT_APTOS>0` but both `QT_COMPARECIMENTO=0` and `QT_ABSTENCOES=0`. They were audited and counted **once by section and round** instead of being silently deleted or treated as ordinary abstention records.

| Year | Nonconserving source rows | Unique exceptional section-round records | Unique exceptional eligible by round |
|---|---:|---:|---:|
| 2022 | 188 | 94 (47 per round) | 657 |
| 2026 | 82 | 41 | 423 |

2022: 156,453,354 eligible on ordinary reconciled rows + 657 exceptional eligible = **156,454,011**, matching the official national total. Exceptions: 46 overseas (`ZZ`) and 1 Amazonas section per round.

2026: 158,745,079 eligible on ordinary reconciled rows + 423 exceptional eligible = **158,745,502** unadjusted. TSE documented **39 temporary-transfer records** excluded from the effective electorate: 158,745,502 − 39 = **158,745,463**. The 39 adjustment is explicit and is **not** assumed to be interchangeable with the 41 exceptional sections.

2022 and 2026 attended totals matched E002 counts exactly for the same years/rounds. All reconciliation checks passed. Implied abstentions are calculated as effective eligible minus attended; they are not naively summed from exceptional `QT_ABSTENCOES` fields.

## Provisional municipal analysis, domestic scope

Full detail files yielded 5,570 matched domestic `(UF, TSE municipal code)` keys between 2022 and 2026, one unmatched domestic 2026 code (`MT/73709`). The full paired file including overseas units (`ZZ`) has 5,708 pairs. A TSE→IBGE code crosswalk is **not yet independently validated**, and the 2022 Amazonas exception affects a local denominator; therefore municipal statistics below remain exploratory.

Using 5,570 domestic paired first-round turnout proportions (no `ZZ`):

- Pearson correlation between 2022 and 2026 municipal turnout proportions: **0.8061**.
- Spearman rank correlation: **0.7885**.
- MAE of naive historical persistence baseline, `|turnout_2026 - turnout_2022|`: **2.1355 percentage points** (unweighted); **1.8973 pp** weighted by the minimum eligible population across years.
- Median municipal percentage-point change: **+0.2041 pp**; 5th and 95th percentiles approximately **−3.3761 pp** and **+5.9611 pp**.

These are **in-sample descriptive cross-election associations**, not forward predictions, not calibrated uncertainty intervals, and not voter-level behavior estimates. Correlations are sensitive to geographic inclusions: retaining the heterogeneous overseas `ZZ` units increases Pearson correlation from 0.8061 to about 0.9069, illustrating a strong scope-composition effect.

## Remaining scientific validation gates

1. Verify TSE→IBGE municipality crosswalk, especially `MT/73709`; reconcile exceptional local denominator for Amazonas.
2. Investigate the 2026 discrepancy of one presidential section between E002 vote-option and E003 section-detail totals.
3. Validate row completeness and the exact meaning of exceptional overseas and temporary-transfer records using TSE dictionary and authoritative documentation.
4. Produce properly versioned municipal feature table with provenance, spatial validation folds, and exclusion rules.
5. Only then fit models with temporally valid covariates, retrospective evaluation and uncertainty quantification.

**Scope restriction:** aggregates for civic and scientific analysis only; no individual preference inference or targeted political persuasion.
