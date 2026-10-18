# E002 — National presidential vote audit

**Research question:** Do official section-level voting ZIPs reproduce
the TSE's finalized national presidential vote totals?

Process **all CSV lines** in each ZIP through the streaming parser:
`python -m electoral_analysis.vote_audit ZIP_FILE --year 2022 --out outputs/national/2022.json`.

The audit classifies NR_VOTAVEL 95 as blank, 96 as null, codes 10–89 as nominal votes, and **reports other codes as unclassified**. It does not infer turnout from vote rows, estimate candidate support by individual or neighborhood, or predict the election.

2022 national reference 1st round: valid 118229719; blank 1964779; null 3487874.
2022 2nd round: valid 118552353; blank 1769678; null 3930765.
Official sources:
- https://www.tse.jus.br/comunicacao/noticias/2022/Outubro/100-das-secoes-totalizadas-confira-como-ficou-o-quadro-eleitoral-apos-o-1o-turno
- https://www.tse.jus.br/comunicacao/noticias/2022/Dezembro/tse-proclama-eleitos-presidente-e-vice-presidente-da-republica-luiz-inacio-lula-da-silva-e-geraldo-alckmin

2026 interim reference (99.99% counted, 2026-10-05) valid 125272513; blank 2300781; null 3674149. **Not final**; do not treat differences as data-integrity errors.
Source: https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/flavio-bolsonaro-e-lula-vao-disputar-o-2o-turno-para-a-presidencia-da-republica

Reports include source checksum and timestamp, total rows, unique sections across rounds, categories and unclassified options. Each CI run publishes small JSON artifacts, not the large original datasets. Official turnout/abstention denominators require separate `detalhe_votacao_secao` files and an additional validation stage.

**No model has been trained and no causal or targeting claims are justified.**
