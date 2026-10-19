# E012 — Análise descritiva histórica e validação estatística

## Comparação de candidaturas entre anos
Variação da participação municipal nos votos válidos = 100 × (votos_c_2026/válidos_2026 − votos_c_2022/válidos_2022), em pontos percentuais.
A comparação entre eleições exige identidade do nome oficial após normalização de acentuação, caixa e espaço. O mesmo número de urna não prova identidade. A base atual tem uma candidatura comparável por esse critério. Não se infere migração individual.

## Censo 2022 × comparecimento
Gráfico de dispersão: um ponto por município da UF selecionada; eixo X log10(1 + população residente) ou log10(1 + densidade); eixo Y comparecimento de 2022 ou 2026, conforme seleção. Pearson r é descritivo, não causal. População residente não é o eleitorado.
Fonte: Censo IBGE 2022 agregado 4714, indicadores 93, 6318 e 614, SHA256 145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641. 5.570 correspondências municipais. A exceção de denominador de 2022 (IBGE 1302603) não entra no gráfico de comparecimento desse ano.

## Métricas observadas E006–E010
| Método | MAE (pp) |
| --- | ---: |
| Persistência | 2,1355 |
| Ridge E006 | 1,9567 |
| Ridge regional E007 | 1,7915 |
| Ridge espacial queen E010 | 1,9455 |
| Ridge espacial rook E010 | 1,9453 |

As cinco métricas refletem validação retrospectiva com 5.569 municípios e 27 folds de UF. A E007 é a menor observada, mas seu desenvolvimento foi exploratório após ver os resultados E006. Os gráficos de Moran global E008 e condicionado intrauf E009 não têm a mesma matriz de pesos e centralização; compará-los como uma redução percentual seria inválido. P-valores exploratórios de 499 permutações não sustentam causalidade.

## Código reproduzível
atlas/analytics.py lê os CSVs científicos oficiais versionados e valida o hash do Censo E006; atlas/build.py exporta os dados integrados; atlas/web/research.js apresenta os gráficos SVG; .github/workflows/e012-research-atlas.yml recompila, testa e versiona o site.

Os dados não medem preferências individuais, não oferecem projeções de votos futuros e não classificam municípios para persuasão política.
