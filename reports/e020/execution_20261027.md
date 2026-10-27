# E020 — Municipal EA20 incremental replay: executed report

Date: 2026-10-27. **Experimental synthetic municipal snapshot replay**, not a restored timeline of TSE real-time publication in the 2026 election.

## Evidence
- GitHub Actions run [40541444642](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40541444642) completed successfully.
- Repository test suite **118 passed**, Ruff passed.
- [Artifact 12750502052](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40541444642/artifacts/12750502052): four simulated raw municipality EA20 responses, receive-time journal, replay.csv, graphs turnout.png/coverage.png plus SVG.
- Simulated two TSE municipality codes in a single UF, with two observations each. Cumulative versions replace earlier versions; **never add national, state and municipality totals together**.
- Four accepted cumulative snapshot records; counts after the final update represent only two municipalities, not the Brazilian nation.

## Constraints

- Offline parser with official EA20 municipal code/scope conventions is implemented and independently tested against **synthetic fixtures**.
- Official TSE municipal live bytes and original real-time receive timestamps were not obtained. The official TSE CDN was not queried during this workflow.
- **EA12/TSE–IBGE crosswalk acquisition, actual municipality collector, full election-year temporal holdout, and E017 regression linkage remain pending.** This stage supplies a municipal state aggregator, not an integrated operational model.
- Graphs are diagnostic, explicitly synthetic, and show *observed participation in reported sections*, not candidate support or unbiased national turnout estimates.
- For true ingestion, use authenticated, hash-preserved original EA20 records and independent municipality mappings. Reference: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

## Next stage

Add trusted raw municipality polling journal and crosswalk; update the municipal regression state only after verifying which specific sections are complete and that municipality-level denominators and partial turnout are compatible with E017's complete-municipality training target.
