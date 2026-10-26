# E014 — Primeiro replay de observações parciais reais

O arquivo `observed_2026_national_partial.csv` reúne **34 registros** históricos de contabilização parcial do segundo turno presidencial de 25 de outubro de 2026: 33 linhas da tabela de evolução de apuração de [Vototeca](https://vototeca.com.br/eleicoes/2026/apuracao) e uma linha observada de 2,42% às 19h20, publicada em [DoubleX.ai](https://eleicao.doublex.ai/). Ambos são arquivos **de terceiros**, associados a fontes do TSE; a verificação criptográfica dos JSON originais na época de publicação não foi possível.

O script `src/electoral_analysis/observed_replay.py` calcula a proporção de votos válidos observada em cada instante e a distância retrospectiva do percentual final: é o desempenho de uma **extrapolação ingênua** (tomar a proporção parcial como se fosse final), não da projeção de Rodrigo Mahlmeister. Não estima intenções, segmenta eleitores ou recomenda ações político-eleitorais.

| Progresso em seções | Desvio absoluto do percentual final |
|---|---:|
| 0,25% | 5,870 pp |
| 2,42% | 0,379 pp |
| 36,77% | 2,101 pp |
| 65,94% | 0,994 pp |
| 84,73% | 0,365 pp |
| 95,89% | 0,056 pp |
| 99,76% | 0,031 pp |

O erro da proporção parcial é não monotônico. Em 2,42% está relativamente perto do resultado final, mas se distancia posteriormente: **uma única observação antecipada não mede calibração ou precisão sustentada de um modelo**.

Para executar: `python -m electoral_analysis.observed_replay --source reports/e014/observed_2026_national_partial.csv --out outputs/e014/observed_replay.json`.

**Pendência científica:** snapshots autênticos de estimativas de Mahlmeister e originais JSON de cada instante, necessários para testar seu erro, cobertura de intervalos e correlações espaciais. Não substituir por série artificial sem identificá-la como tal.
