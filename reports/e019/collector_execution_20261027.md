# E019 — Audited EA20 collector: execution report (2026-10-27)

**Status:** implemented, 114 repository tests passed; official-data collector verified against published EA20 schema, and end-to-end simulation passed. **No historical live election-night snapshots have been captured.** This stage is infrastructure, not evidence of real-time predictive skill.

## Source verification

Official TSE technical documentation: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados

Official EA20 nationwide source: https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json

Observed published final EA20 includes top-level ele=6258, carg[].cd=1, s.ts (total sections), s.sa (counted sections), e.esa (registered electorate of counted sections), e.c (actual attended), dg/hg (generation time in Brasília), idg (file-generation identifier). **Important:** s.st (totalized sections) is *not* automatically equivalent to s.sa (counted sections). The normalized replay preserves s.sa semantics.

## Implementation

- `src/electoral_analysis/tse_official_collector.py`: strict allowlisted URL, HTTPS-origin restriction, 2MB cap, UTC-converted source and receiver time, conditional HTTP GET, content-addressed raw JSON preservation, append-only JSONL journal, verified CSV export to E018 replay.
- `tests/test_tse_official_collector.py`: fixture-driven schema, generation time, data identity, no future leak, 304/idempotence, checksum tampering and redirects.
- `docs/e019_protocol.md`: operational instructions and limitations.
- `.github/workflows/e019-official-tse-archive.yml`: reproducible integration with **SYNTHETIC** successive EA20 replies only, to avoid claiming past-live capture.

## Reproducibility

GitHub Actions succeeded: https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40509018068

- Full test suite and Ruff: green.
- Four explicitly synthetic cumulative source replies archived.
- Four normalized E018 replay events produced.
- Two charts as PNG and SVG: `figures/turnout.png`, `figures/coverage.png`.
- GitHub artifact: https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/40509018068/artifacts/12736072801

## Important blockers

1. One national snapshot **does not** reveal the actual municipality-by-municipality or section-by-section arrival order. To link with E017 online Ridge, the next integration needs official **non-overlapping municipality snapshots** with verified TSE mapping and denominators (not additive national+state+municipal snapshots).
2. The endpoint currently provides the final published 2026 outcome. Polling it today **cannot recreate the sequence of intermediate snapshots observed on 25 October 2026**.
3. This experiment **does not implement** future-election temporal validation; that requires an actual heldout election year and historically available covariates. All 2026-only validation remains exploratory.
4. The journal records acquisition time only when collector actually runs. It is not a continuously scheduled polling service.

## Scientific conclusion

Verified foundation for immutable source collection and reproducible replay; **no inference yet that online projection accuracy improves**. Continue with an audited municipal adapter and independent temporal validation without modifying the E014–E017 baselines.
