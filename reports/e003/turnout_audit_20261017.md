# E003 — National turnout and provisional municipality comparability

**Date:** 2026-10-17. **Status:** full-data computation completed, national vote-count reconciliation passed; eligible-voter and anomalous-section reconciliation pending.

## Verified execution

GitHub Actions: [run 39049428382](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39049428382). This workflow downloaded the official TSE national `detalhe_votacao_secao` ZIPs for 2022 and 2026, streamed all state and BRASIL CSV members, selected `DS_CARGO=Presidente`, deduplicated repeated section/round keys and produced national/municipal aggregates. Associated [artifact](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39049428382) contains both complete JSON audits, source SHA256 manifests and a provisional municipal comparison. The raw national ZIPs were **not** stored permanently in Git.

| Year/round | Sections accepted | Eligible (accepted rows) | Attended | Abstained (accepted rows) | Turnout among accepted rows |
|---|---:|---:|---:|---:|---:|
| 2022, 1 | 472,028 | 156,453,354 | 123,682,372 | 32,770,982 | 79.0538% |
| 2022, 2 | 472,028 | 156,453,354 | 124,252,796 | 32,200,558 | 79.4184% |
| 2026, 1 | 499,207 | 158,745,079 | 125,275,835 | 33,469,244 | 78.9164% |

**National reconciliation:** `attended` matches the total ballot counts independently computed from the official national vote-by-section ZIPs in E002 for all three year/round combinations. This is a useful independent consistency check, **not** a validation of the eligible-voter denominator.

## Data-quality findings

- 2022: 29 CSV members; **188** nonconserving presidential *rows* quarantined before aggregation; 944,056 repeated identical section/round rows deduplicated.
- 2026: 30 CSV members; **82** nonconserving presidential *rows* quarantined; 499,207 repeated identical section/round rows deduplicated.
- Quarantined rows violate `QT_APTOS = QT_COMPARECIMENTO + QT_ABSTENCOES`. Numerous inspected examples have `SG_UF=ZZ` (overseas voting), `QT_APTOS>0`, and zero attended/abstained. Their meaning must be verified using TSE documentation; **do not assume these are corrupt**.
- As a consequence, reported `eligible` counts are sums of **accepted rows only**; they may exclude exceptional eligible voter records. National turnout rates are descriptive **provisional** estimates, not final reconciled turnout rates.
- Unique presidential section/round counts from the detail file differ by **one** in 2026 from the E002 voting-by-section file (499,207 vs. 499,206). Investigate this before interpreting granular statistics.
- The 2026 TSE notice regarding **39 temporary-transfer records** requires a separate denominator reconciliation; do not equate this with the 82 exceptional rows without evidence.

## Municipal comparison

Provisional identity matching by `(SG_UF, CD_MUNICIPIO)` for first rounds finds **5,708** paired keys, **2** keys only in 2022, and **9** only in 2026. These are **TSE codes**, not verified crosswalks to IBGE codes. Local administrative/overseas special cases and changes in registry must be checked before publishing a longitudinal municipality-level inference. No city has been attributed to a voter and no election audience is profiled.

For transparency, the difference in the aggregate accepted-row turnout fractions for first rounds is approximately **-0.1375 percentage points** (2026 minus 2022). This is a *provisional arithmetic difference* and not an individual change, a forecast, a causal effect or an official TSE headline.

## Methodological gates before statistical modeling

1. Review **all** nonconserving rows, not just the 50 stored diagnostic examples per year; classify by UF/round/origin and preserve counts without silent corrections.
2. Investigate section key difference (499,207 vs 499,206) and source-date alignment.
3. Validate eligible/abstention counts against official TSE national and UF round totals. Record whether extraordinary overseas/transfer registers belong in denominators.
4. Produce an authoritative TSE–IBGE municipality code crosswalk; flag no-match and many-to-one cases.
5. Validate population/registration chronology, geographic continuity and absence of temporal leakage.
6. Only then promote municipal comparative indicators from **provisional** to **validated** and evaluate descriptive/statistical baselines.

### Scope

This is aggregate electoral statistics research. It does not infer individual vote preferences, produce voter persuadability scores, segment people for political targeting or optimize electoral messaging.
