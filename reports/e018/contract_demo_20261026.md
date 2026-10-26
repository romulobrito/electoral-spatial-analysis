# E018 — Incremental snapshot replay, synthetic contract validation (26 Oct 2026)

**Status:** source-independent normalization/replay layer implemented; **not yet a connected live official TSE ingestion**, and **not independent temporal validation**.

GitHub Actions run: https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40404798214 (success). All 107 tests passed and Ruff succeeded. Synthetic demo artifact: https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40404798214/artifacts/12689838183 .

The demo consists of four **synthetic** cumulative snapshots from two fictional reporting units. Generated figures include `figures/turnout.png`, `figures/coverage.png` and corresponding SVGs. The figures are contract/logic demonstrations and should **never** be described as real TSE apuração observations.

## Delivered
- Strict normalized CSV schema with independent `source_generated_utc` and `received_utc`.
- Idempotent deduplication and stale event handling; identical duplicate bytes are not double counted.
- Non-regressing section/eligible progress controls and explicit correction handling for attended counts.
- Replay aggregates only reported-section attendance and eligibility; no inference for unrevealed sections.
- SHA256 source-identifier field and event-manifest input checksum.
- Five synthetic defensive tests plus existing suite, PNG/SVG charts.

## Crucial limitations
- Input `source_sha256` syntax is checked, but no raw-TSE-source hash is authenticated yet; an adapter and immutable archive are required.
- Official TSE partial results can be cumulative and coarse; one must verify true geography, timestamps and denominators from observed source schema before consuming.
- Coverage is among **currently observed reporting units**, not necessarily national reporting coverage when units have not all entered the stream.
- Observed turnout of reported units is subject to order selection, so this module **does not estimate final national turnout**, let alone candidate votes.
- Independent temporal experiments using historical elections are still outstanding, because E014–E017 compare synthetic reveal orders of the same 2026 election.

**Next research gates:** acquire authenticated historic publication snapshots or official section-level observations with timestamps; develop source-specific schema adapter; verify geographic crosswalk, versioning and national conservation; add as-of historical features; run time-separated backtest with no heldout-year tuning. Keep E018 prototype branch separate from research claims of operational readiness.
