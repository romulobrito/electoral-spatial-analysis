# E002 — Audit of official presidential vote tallies, 2022 and 2026

Date: 2026-10-17. **Observed calculations, not electoral forecasts.**

## Provenance

Full national official TSE voting-by-section ZIPs were downloaded and streamed in GitHub Actions run [39046994539](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39046994539). The two matrix jobs completed successfully. The ZIP files were not committed or archived. Compact JSON results with state-level aggregations, vote-option totals, extraction timestamp and SHA256 were retained as workflow artifacts (14 days).

| Year | Input rows | Unique presidential section-round keys | Download ZIP SHA256 |
|---|---:|---:|---|
| 2022 | 5,380,736 | 944,056 | `9353993de5cf03778aef44e01d4925e7ee105f5262491d344a2f0dbc956b0139` |
| 2026 | 3,800,511 | 499,206 | `2d42006d0f6c6e00bad83f5c23cd3d78cd3e3182dbc1ad6718222b6b132c23e1` |

Section-round keys are counted for each round separately: 944,056 is **not** the number of distinct physical sections across both elections. Also, tally rows and registered/eligible voters are different concepts.

## National voting results obtained from ZIP

| Election | Valid candidate votes | Blank | Null | Total counted | Unclassified |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022, round 1 | 118,229,719 | 1,964,779 | 3,487,874 | 123,682,372 | 0 |
| 2022, round 2 | 118,552,353 | 1,769,678 | 3,930,765 | 124,252,796 | 0 |
| 2026, round 1 | 119,306,034 | 2,300,798 | 3,669,003 | 125,275,835 | 0 |

The valid/blank/null quantities in **both** 2022 rounds match the configured TSE 2022 references exactly; all six checks have zero difference. These references should still be accompanied by exact URLs and dated snapshots in the final scientific paper.

### Issue requiring investigation: 2026 published reference

TSE article dated 2026-10-05, with 99.99% of ballot boxes counted, states 125,272,513 "votos válidos", 2,300,781 blank, and 3,674,149 null. The downloaded later ZIP yields 119,306,034 candidate-valid votes, 2,300,798 blank, 3,669,003 null, and 125,275,835 total counted votes.

The first article value closely resembles **total counted votes**, not candidate-valid votes. Therefore the article's categories are **not a validated apples-to-apples reference** for the current ZIP. The earlier code annotation that implied an exact valid-vote comparator was erroneous and has been corrected to mark this benchmark non-comparable. Do not infer a discrepancy in official raw data from this article alone. Reconcile against a dated authoritative final-election table or TSE results export.

TSE article: https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/flavio-bolsonaro-e-lula-vao-disputar-o-2o-turno-para-a-presidencia-da-republica

## Method

Read one CSV directly from each national ZIP using a streaming DictReader, restrict `DS_CARGO=Presidente`, validate year/round/counts/geographic keys, classify `NR_VOTAVEL` (95 blank, 96 null, two-digit candidate options as valid), and accumulate national/UF and option totals. Unrecognized options are surfaced separately rather than dropped. No row-level personal data were inferred or enriched.

This script does **not** measure turnout or abstention; official section-detail files are required for those denominators. Municipal longitudinal comparisons also require validated TSE municipality keys and geographic continuity. Candidate share differences are not evidence of individual vote transitions.

## Next validation gates

1. Validate 2026 categories against an authoritative *final* 2026 TSE totalization export and record its publication date.
2. Add checks comparing sum of states to national totals, unique sections by round, and candidate codes to TSE candidacy records.
3. Download/detail-audit section turnout ZIPs for 2022 and 2026; handle transfer-voter caveats.
4. Produce national and municipal descriptives only after reconciliation. No predictive model fit has been performed.

Artifacts:
- [2022 audit](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39046994539)
- [2026 audit](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39046994539)

## Independent arithmetic checks (2026-10-17)

The downloaded GitHub Actions JSON artifacts were independently inspected. For every category (`valid`, `blank`, `null`, `unclassified`) in 2022 rounds 1 and 2 and 2026 round 1, both (a) the sum of the 28 `state_aggregates` groups (27 UFs and exterior) and (b) the sum of records in `candidates_and_vote_options` reproduce the corresponding national values **exactly**: 12 of 12 category-round reconciliation cases passed by both routes. The national three-row snapshot is versioned at [`national_voting_totals_20261017.csv`](national_voting_totals_20261017.csv). The input SHA256 is in every row, allowing repeatable validation when source archives are re-downloaded.

**Important:** these checks confirm internal arithmetic consistency, not that every original vote record is valid or that any geographic matching between years has been established. The dated 2026 TSE article remains an ambiguous reference, not proof of an incorrect national archive.
