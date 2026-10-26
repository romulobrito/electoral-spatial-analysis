# E014 — Stress test da ordem contrafactual de revelação municipal

**Execução local reproduzida sobre o painel TSE E005 SHA256** `2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d`, com dados municipais reais de **comparecimento no primeiro turno de 2026** e referências de 2022. **Todas as 245 sequências são simuladas**, não a ordem verdadeira do TSE, e o resultado não mede apoio a candidaturas nem reproduz o modelo de projeção de Rodrigo Mahlmeister.

Amostra: 5.569 municípios, 27 UFs; exclusão previamente auditada de `1302603`. São 120 ordens aleatórias uniformes, 120 ordens aleatórias balanceadas por UF, cinco ordens determinísticas (menor ou maior comparecimento histórico, maior ou menor eleitorado e UF em blocos). Semente **20261026**; revelação por município completo, nunca por seção. Metas do experimento por percentual do **eleitorado contido nos municípios revelados**, não percentual das seções eleitorais: 0,25%, 1%, 2,5%, 5%, 10%, 25%, 50%, 75%, 95%. A indivisibilidade municipal pode ultrapassar cada meta.

O valor final observado do comparecimento no recorte é **79,1235%**. A média histórica de 2022 reponderada pelo eleitorado municipal de 2026 é **79,2185%**; a diferença é 0,0950 pp — coincidência amostral histórica que não demonstra generalização.

## Erros absolutos em 2,5% de cobertura do eleitorado (pp)

| Cenário artificial | Percentual parcial ingênuo | Mudança nacional histórica | Correção UF contraída |
|---|---:|---:|---:|
| 120 ordens uniformes (média) | 0,848 | 0,510 | 0,480 |
| 120 ordens balanceadas por UF (média) | 1,257 | 0,617 | 0,514 |
| Histórico de menor comparecimento primeiro | 6,330 | 4,385 | 4,243 |
| Histórico de maior comparecimento primeiro | 6,254 | 1,093 | 1,157 |
| Municípios por blocos de UF | 0,403 | 1,983 | 1,984 |

O estimador histórico nacional aplica a mudança observada entre comparecimento 2022 e 2026 nos municípios já revelados aos demais municípios. A variante de UF calcula mudança em cada UF e contrai em direção à nacional, usando pseudocontagem fixa de 30 municípios. O percentual ingênuo calcula somente a média ponderada dos já revelados. Todos utilizam comparecimento corrente apenas das unidades previamente reveladas; valores escondidos são usados **somente para pontuar o erro**.

Os resultados evidenciam a sensibilidade a padrões de seleção territorial. Em especial, correção de swing pode piorar a extrapolação em cenários de concentração geográfica mesmo quando reduz erro médio sob ordens aleatórias.

**Limitações:** a base estudada é de participação no **primeiro turno**; não é uma reprodução da apuração de votos válidos do **segundo turno**; o percentual de seções e a cobertura do eleitorado não são equivalentes. Não se pode transferir estes números como avaliação da projeção fechada de Mahlmeister. As 120 ordens não constituem eleições independentes; nenhuma cobertura de intervalo preditivo foi demonstrada.

### Reprodução

O script `src/electoral_analysis/arrival_selection_stress.py` verifica SHA256 do painel e reproduz os resultados:
`python -m electoral_analysis.arrival_selection_stress --panel outputs/e005-results/municipal_results.json --out-dir outputs/e014/selection-stress --reps 120 --seed 20261026`.

A auditoria dos 34 registros parciais nacionais históricos (outro recorte e outra métrica) permanece separada em `reports/e014/observed_2026_replay.md`.
