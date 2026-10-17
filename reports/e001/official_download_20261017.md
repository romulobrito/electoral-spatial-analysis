# E001 — Verified TSE voting-section download (2026-10-17)

## Scope and execution

GitHub Actions run [39045993206](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39045993206), workflow `Verify official TSE ZIP downloads`, successfully downloaded both **national presidential voting-by-section ZIPs** from official TSE CDN. This runner was used because local runtime DNS could not resolve `cdn.tse.jus.br`. Evidence includes HTTP HEAD output, downloader execution logs, SHA256 manifest, ZIP member inventory and CSV header in two small GitHub Actions artifacts (retained for 14 days).

| Election | HTTP | ZIP bytes | SHA256 | Uncompressed CSV bytes |
| --- | --- | ---: | --- | ---: |
| 2022 | 200 | 271292455 | `9353993de5cf03778aef44e01d4925e7ee105f5262491d344a2f0dbc956b0139` | 1591148802 |
| 2026 | 200 | 161616519 | `2d42006d0f6c6e00bad83f5c23cd3d78cd3e3182dbc1ad6718222b6b132c23e1` | 1052510851 |

Resources:

- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_BR.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip`

Archive members: `votacao_secao_2022_BR.csv` / `votacao_secao_2026_BR.csv`, plus `leiame.pdf` in each. CSVs were inspected **without full extraction**; both show the same 26-column header:

```
DT_GERACAO; HH_GERACAO; ANO_ELEICAO; CD_TIPO_ELEICAO;
NM_TIPO_ELEICAO; NR_TURNO; CD_ELEICAO; DS_ELEICAO;
DT_ELEICAO; TP_ABRANGENCIA; SG_UF; SG_UE; NM_UE;
CD_MUNICIPIO; NM_MUNICIPIO; NR_ZONA; NR_SECAO;
CD_CARGO; DS_CARGO; NR_VOTAVEL; NM_VOTAVEL;
QT_VOTOS; NR_LOCAL_VOTACAO; SQ_CANDIDATO;
NM_LOCAL_VOTACAO; DS_LOCAL_VOTACAO_ENDERECO
```

**Interpretation:** voter-count totals and turnout cannot be obtained by summing the `QT_VOTOS` column as if it represented unique eligible voters. The file is a voting-by-candidate/option table. Use the distinct TSE *detail-by-section* data, after validating its true schema, for eligible/turnout/abstention denominators. For official vote-share measures, sum verified compatible `QT_VOTOS` records by office, round, geography and candidate; distinguish valid candidate votes from blank/null choices.

**Scientific status:** real source downloads and headers verified; no full extraction, no row-level schema validation, no counting reconciliation, no model fitting or election analysis was performed. GitHub runner copies of the two large ZIP files are temporary and were **not uploaded as workflow artifacts or committed**. Only compact provenance/diagnostic archives were retained.

### Diagnostic evidence (GitHub artifacts)

- [2022 artifact](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39045993206/artifacts/12105787444)
- [2026 artifact](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39045993206/artifacts/12105702781)

### Next reproducibility gates

1. Run a streaming parse of the official CSVs to compute record counts, contest/round breakdown and data-quality checks.
2. Download detail-by-section archives and verify their schema before comparing turnout/abstention.
3. Record authoritative TSE aggregates to reconcile totals without arbitrary adjustments.
4. Preserve compact, non-personal aggregate audit outputs (not multi-GB national raw CSVs) in permanent versioned reports.
