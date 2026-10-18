# E004 — Official TSE–IBGE municipal harmonization (17 October 2026)

## Observed execution and provenance

GitHub Actions [run 39051641225](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39051641225) finished successfully and streamed both full 2022 and 2026 TSE turnout-detail archives. The resulting [artifact](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39051641225/artifacts/12107499421) retains detailed aggregated municipal/round diagnostics and the full preliminary code-IBGE comparison. No large source ZIPs are committed.

Crosswalk: `https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip`, a TSE resource with internal CSV generation date 11 October 2026 and SHA256 `68328ddc166806594a2aab5809ac9aa602153535d6b8a71e886c337f9f3631ca`.

The official CSV contains `SG_UF`, `CD_MUNICIPIO_TSE`, `CD_MUNICIPIO_IBGE`, among others. TSE IDs are canonicalized numerically (e.g., `01007` and `1007`); IBGE IDs retain seven digits. Exact matches are required, and ambiguous or many-to-one mappings raise errors.

## Harmonization results

| Quality gate | Observed |
|---|---:|
| First-round municipalities matched in both years | **5,570** |
| Only in 2022 | **0** |
| Only in 2026 | **1** |
| Unmapped TSE codes in 2022 | **0** |
| Unmapped TSE codes in 2026 | **0** |
| Conflicting TSE-to-IBGE crosswalk rows | **0** |
| Duplicate crosswalk rows | **0** |

There is one municipality appearing in 2026 but not in the available 2022 municipal tally (previous diagnostic identified TSE key `MT/73709`). It is **not imputed as zero in 2022**; a matched-sample historical comparison excludes it.

The matched-pair sample's unweighted mean percentage-point change in local turnout rate was **+0.5533 pp**, and median **+0.2041 pp** (rates from accepted, conserving section records). This is NOT the national aggregate turnout change and does not imply an increase in individual participation at a given location. Statistics remain exploratory.

## Residual validation and provenance risks

1. **2022 exceptional Amazonas section:** The official 2022 detail file contains a quarantined presidential section `(SG_UF=AM, CD_MUNICIPIO=2550, NR_ZONA=68, NR_SECAO=797)` with 84 eligible, zero attended and zero recorded abstentions. The national eligible reconciliation includes the exceptional 84 in the effective denominator, while the provisional municipality-level row currently excludes it. An independently justified geographic allocation (rather than silent reassignment) is needed before certifying municipal turnout rates.
2. **2026 section discrepancy — investigated and explained:** The independent [full source symmetric-difference run 39051880881](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39051880881) found 499,206 distinct vote-file section keys and **499,248** detail-file keys including 41 exceptional zero-attendance records. It found **42 detail-only zero-attendance keys** (41 quarantined exceptional sections and one otherwise conserving zero-attendance section), no vote-only keys, and no attendance/vote-total disagreement across shared keys. Thus the original 499,207 *accepted* detail-key count exceeds 499,206 vote keys by one for a valid zero-attendance section. This is a coverage distinction, not evidence of missing votes.
3. **Registration changes:** Identical IBGE municipality geography is appropriate for broad municipal comparison, but the registered electorate changes between years. Geographic identity is not an individual panel.
4. **Model validity:** No supervised spatiotemporal prediction, credible interval calibration, retrospective forward-test or spatial block test has yet been run. Associations are descriptive only; do not claim a forecasting model.

## Next reproducible investigation

Implement an explicit section key symmetric-difference check against the 2026 national voting ZIP; report any difference with total votes and election/round identity. Allocate exceptional Amazonas section only after a supported source-data interpretation. Once resolved, produce a frozen 2022/2026 municipality table with accepted-denominator indicators and an exception flag. No voter-level political inference or targeted campaign optimization.
