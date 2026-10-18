# E001 — Official source inventory and section-turnout audit

**Status: implementation tested against synthetic fixtures; official downloads NOT executed.**

## Source verification (2026-10-17)

The TSE datasets list four relevant ZIP resources:

| key | Official file |
| --- | --- |
| president_2022 | `votacao_secao_2022_BR.zip` |
| president_2026 | `votacao_secao_2026_BR.zip` |
| turnout_2022 | `detalhe_votacao_secao_2022.zip` |
| turnout_2026 | `detalhe_votacao_secao_2026.zip` |

Sources: https://dadosabertos.tse.jus.br/dataset/resultados-2022 and https://dadosabertos.tse.jus.br/dataset/resultados-2026 . ZIP links were confirmed from public resource listings, but **actual file schemas have not yet been empirically validated**.

## 2026 national caveat

The TSE warns about 39 temporary-elector-transfer records retained at sections of origin, quoting 158,745,502 registrations before adjustment and 158,745,463 as the effective total. This is a national caveat, not permission to subtract 39 from arbitrary municipal or section counts. Reconciliation requires official methodology and source-specific evidence.

## Commands

```bash
python -m electoral_analysis.cli sources
python -m electoral_analysis.cli download turnout_2022 --output-dir data/bronze/2022
python -m electoral_analysis.cli download turnout_2026 --output-dir data/bronze/2026
python -m electoral_analysis.cli audit-turnout data/bronze/2022/turnout_2022.zip --year 2022 --member VERIFIED_CSV_NAME --output outputs/e001/turnout_2022.json
```

Select the verified CSV member if an archive contains multiple CSVs. Any use of `--max-rows` marks the report partial and makes it unsuitable for scientific inference.

## Validation gates before modeling

1. Inspect genuine ZIP member names and the official dictionary, including the contest field.
2. Confirm TSE municipality codes are not IBGE municipality IDs; do not join without a crosswalk.
3. Reconcile totals against TSE authoritative results for the same year and round.
4. Investigate the impact of the 39-record caveat for the relevant geography.
5. Preserve SHA256, source retrieval timestamp, input row count, script SHA, and audit results.
6. Only after passing these gates, compute observed historical changes and fit descriptive baselines.

## Results and limitations

11 local unit tests passed on **synthetic** CSV/ZIP fixtures. No real election ZIP was obtained in this environment. No empirical turnout totals, spatial patterns, model validation or political-targeting output has been generated. Aggregate election data cannot reveal individual voting transitions.
