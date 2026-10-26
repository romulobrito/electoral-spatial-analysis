# E014 — Protocolo de auditoria temporal de projeções

**Objetivo:** avaliar retrospectivamente projeções **já arquivadas**, verificando erro, viés, largura/cobertura de intervalos e Moran espacial municipal, sempre nos instantes de publicação. **Não é um sistema de previsão eleitoral.**

## Dados necessários

`projections.csv`: `election_id,model_id,metric_id,unit_id,uf,snapshot_utc,data_asof_utc,progress_fraction,estimate_pct,lower95_pct,upper95_pct,source_sha256`

`truth.csv`: `election_id,metric_id,unit_id,uf,final_pct`

`edges.csv` (opcional): `unit_a,unit_b`

Horários UTC em formato `Z`; porcentagens de 0 a 100; progresso de 0 a 1, com denominador idêntico entre métodos comparados. `snapshot_utc` é o horário em que a estimativa estava disponível e `data_asof_utc` é o último dado utilizado. O validador rejeita dado de horário futuro e progressos decrescentes; isso é condição necessária, **não prova suficiente** de ausência de vazamento. O SHA256 declarado deve ser conferido contra o arquivo original em auditoria separada.

## Análise

- Erro absoluto médio, RMSE, viés, cobertura empírica e largura de intervalos de 95%, em faixas predefinidas de 0–1%, 1–2,5%, 2,5–5%, 5–10%, 10–25%, 25–50% e 50–100%.
- Comparação pareada para mesma eleição, métrica, município, instante e progresso; bootstrap por **eleições completas** apenas se houver pelo menos três eleições. Repetições temporais/municipais não são eventos independentes.
- Moran's I descritivo dos resíduos municipais em grafo de vizinhança documentado, restrito a mesma UF. Não fornece p-valores.
- Erro municipal médio **não** é erro de projeção nacional ponderado.

## Estado

E014 não reproduz o algoritmo fechado de Rodrigo Mahlmeister. Apenas audita estimativas externamente arquivadas. O atlas e resultados municipais de E013 não contêm por si só snapshots contemporâneos da apuração 2026. Não reconstruir os arquivos parciais a partir dos finais e não reportar métricas sintéticas como observações reais.

Referências: https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados e https://github.com/romulobrito/electoral-spatial-analysis/blob/main/reports/e013/README.md .
