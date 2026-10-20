# E013 — Relatório de resultados multivariados e diagnóstico espacial

**Status:** experimento oficial executado com sucesso na [GitHub Actions #39326818185](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39326818185), artefato GitHub #12222407757; 76 testes passaram. Resultados abaixo transcritos do log estruturado dessa execução, sem substituição por valores simulados. A tabela resumida em JSON desta etapa é `reports/e013/summary.json`. O artefato da execução contém a saída integral.

## Pergunta e método

Investigou-se se um modelo multivariado não linear, com preditores de 2022, melhoraria a reconstrução retrospectiva da **variação do comparecimento municipal entre 2022 e 2026**, além de reduzir autocorrelação espacial residual. A validação manteve 5.569 municípios e 27 folds com uma UF inteira fora do treino; nenhuma variável de comparecimento de 2026 da UF reservada entrou no treinamento. O modelo E007 foi reproduzido exatamente antes da comparação. Os termos quadráticos e a penalização (alpha=10) foram fixos; correções regionais calculadas exclusivamente no treino.

## Erro fora da UF de treinamento

| Modelo | MAE (pp) | RMSE (pp) | Δ MAE vs E007 (pp) | IC 95% bootstrap por UF para Δ |
|---|---:|---:|---:|---|
| Persistência | 2,1355 | 2,8577 | — | — |
| Ridge E006 | 1,9567 | 2,5024 | — | — |
| **Ridge regional E007** | **1,7915** | **2,2862** | 0 | Referência |
| Quadrática E013 | 1,9383 | 2,5226 | +0,1468 | [−0,0244; +0,3327] |
| Quadrática regional E013 | 1,8167 | 2,3482 | +0,0252 | [−0,0380; +0,1147] |

**Interpretação:** os modelos quadráticos não superaram numericamente a ridge regional. Ambos os intervalos de diferença de MAE incluem zero; não há evidência inferencial robusta de diferença para a métrica e procedimento exploratórios adotados. Menor MAE é melhor. A escolha de termos quadráticos foi posterior às análises exploratórias anteriores e não corresponde a uma hipótese confirmada em eleição futura.

## Associações multivariadas descritivas

A regressão OLS contém efeitos fixos de UF e três preditores padronizados; intervalos de coeficientes agrupados por UF (27 grupos). Resposta: mudança de comparecimento em **pontos percentuais**. `R²=0,4879` é **dentro da amostra**, influenciado pelos efeitos fixos, e NÃO mede previsões em UFs não vistas.

| Preditor | Coeficiente (pp / 1 DP) | IC 95% | R² parcial amostral |
|---|---:|---|---:|
| Comparecimento em 2022 | −1,5119 | [−1,8884; −1,1355] | 0,2525 |
| log(1+população IBGE 2022) | −0,2377 | [−0,4573; −0,0182] | 0,0064 |
| log(1+densidade IBGE 2022) | +0,2436 | [+0,0426; +0,4447] | 0,0051 |

Os coeficientes de população e densidade são pequenos e os respectivos R² parciais são baixos, após controlar comparecimento histórico, o outro indicador do Censo e a UF. O coeficiente negativo de comparecimento histórico na mudança subsequente pode envolver regressão à média, efeitos de limites e outros mecanismos não identificados. Não é inferência causal.

## Organização espacial que permanece

| Resíduos fora da UF | Moran I condicionado na UF, queen | p permutacional |
|---|---:|---:|
| Ridge regional E007 | 0,2849108 | 0,002 |
| Quadrática regional E013 | 0,2849014 | 0,002 |

Ambas utilizam 5.566 nós conectados e 499 permutações condicionadas à UF. A alteração de Moran I é praticamente nula (−0,0000094). Logo, elevar a complexidade polinomial sem novas variáveis/estrutura não resolveu a dependência espacial residual.

## Conclusão e próxima hipótese

É recomendável **manter a ridge regional E007 como baseline**, sem promover a E013 quadrática como melhoria. A pergunta científica prioritária passa a ser quais fatores territoriais não capturados pelo conjunto de variáveis de 2022 se associam ao comparecimento e aos padrões dos resíduos. Qualquer extensão precisa de validação geográfica e incerteza, controle de confundimento e evidência externa; não se deve tratar associação agregada como preferência individual nem como recomendação político-eleitoral.

**Fontes imutáveis:** painel TSE E005 SHA256 `2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d`; Censo E006 `145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641`; IBGE Malha 2022 `9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2`.
