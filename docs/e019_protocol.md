# E019 — EA20 national result archive, official TSE

**Scope:** neutral, aggregate observed turnout for the 2026 Brazilian presidential election, not candidate-vote forecasting. This is a live-ready **collector**, not proof that any historical reporting snapshots were captured. E014–E017 remain retrospective municipal reveal simulations.

## Verified official interface

- Official TSE technical instructions: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados
- 2026 federal first/second round election IDs 6257/6258.
- Official cumulative BR EA20 JSON: https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json
- On the observed final EA20 JSON (25 Oct 2026), top-level election identifier and scope are ele=6258, tpabr=br, cdabr=br. Presidential cargo carg[].cd=1. Source-generated date/time use dg/hg (Brasília local time), source version idg. **Seções apuradas** s.sa, total s.ts, electorate in counted sections e.esa, observed turnout e.c. Section totalization (s.st) is a distinct statistic and MUST NOT be silently substituted for s.sa.
- Detailed TSE layout and privacy/consumption constraints take precedence over third-party interpretations.

## Commands

Collect ONE live official snapshot; there is no background job:

\`\`\`bash
python -m electoral_analysis.tse_official_collector \
  --election 6258 --archive outputs/e019/archive --export outputs/e019/events.csv \
  --max-polls 1
\`\`\`

The command writes original bytes under raw/<SHA256>.json, an append-only JSONL journal (including receipt time, URL, HTTP caching and normalized values), and an independently verified export compatible with E018. If source bytes differ at identical SHA256 path, export fails. The endpoint is allowlisted; response size is capped at 2 MB; redirects to other hostnames are rejected; conditional GET is supported. Time is actual time of collection. Multi-poll commands must use at least a 30-second interval; prefer at least 60 seconds to respect the TSE CDN.

## Important limitations

- The TSE's final EA20 downloaded after the election **cannot reconstruct** historical intermediate timestamps or the actual order in which municipality/section results were received.
- The collector reads one **national cumulative snapshot**. It does **not** reconstruct which individual municipalities or sections contributed to each update, and cannot directly drive the E017 municipal regression. That requires adding the official UF/municipality progression EA14/EA15 configuration and/or EA20 municipality snapshots with unique geographies and verified denominator semantics.
- A single official final JSON can be treated as an empirical aggregate observation, never as a demonstration of real-time model skill or live polling.
- Robustness to invalid content is tested using explicitly synthetic JSON fixtures; automated GitHub Actions does not claim historical live connectivity.
- For genuine independent temporal validation, separate complete elections and as-of historical features are required; comparing heldout synthetic 2026 arrival orders does not suffice.

## Next tasks

Expand to verified official municipality results and test non-overlapping aggregation; collect immutable observations during a **future** live event; study revision handling with a real version archive, and compare real received-time trajectory to synthetic arrivals. Report figures based on actual archived intermediate snapshots only when authenticated and distinct in time.
