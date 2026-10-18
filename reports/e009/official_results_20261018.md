# E009 — Moran condicionado às UFs nos resíduos de comparecimento

**Data da análise:** 18 de outubro de 2026. **Status:** execução completa concluída com sucesso, **57 testes aprovados** e Ruff aprovado. O estudo utiliza **apenas comparecimento eleitoral agregado**, nunca votos previstos em candidaturas, perfis de eleitores ou segmentação para persuasão política.

## Evidências e arquivos

- [GitHub Actions E009: execução 39125867023](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39125867023) — sucesso.
- [Artefatos JSON, CSV e SVG da execução](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39125867023/artifacts/12135823570) — retenção limitada a 14 dias.
- Fonte geográfica: **IBGE Malha Municipal Digital 2022**, 5.572 geometrias EPSG:4674, SHA256 `9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2`.
- Painel eleitoral E005 (TSE 2022/2026) e Censo IBGE E006 recuperados de artefatos com **checksums originais verificáveis**, preservando a harmonização municipal oficial efetuada em E004. Resíduos de validação por UF da E007 recalculados, com verificação numérica de seus MAEs.

## Hipótese e protocolo

A E008 documentou Moran I global de aproximadamente 0,40 a 0,50 nos resíduos de comparecimento municipal. Entretanto, **um Moran global elevado pode ser influenciado por mudanças de média entre UFs**. Para investigar dependência intrauf, a E009:

1. Remove todas as arestas que conectam polígonos de UFs diferentes nos grafos *queen* e *rook* da malha original;
2. Exclui da estatística os municípios sem vizinhos dentro da própria UF, sem removê-los da base original;
3. Centraliza cada vetor residual pela média **dos nós conectados da respectiva UF**;
4. Calcula Moran I com pesos de vizinhança padronizados por linha;
5. Realiza 499 permutações de Monte Carlo **somente dentro de cada UF**, seed 2718. O teste bilateral é centralizado na **média empírica** da distribuição nula condicional; não reutiliza a expectativa de Moran global `-1/(N-1)` sem justificativa.

Essa transformação muda o conjunto de nós, os pesos e a centralização. **Os valores de Moran das E008 e E009 não podem ser comparados numericamente como se a estatística e o grafo fossem idênticos.**

## Integridade dos grafos intrauf

| Indicador | Queen | Rook |
| --- | ---: | ---: |
| Arestas originais na E008 | 16.455 | 15.986 |
| Arestas cruzando UFs, removidas | **1.212** | **1.198** |
| Arestas dentro de UFs | **15.243** | **14.788** |
| Municípios modelados inicialmente | 5.569 | 5.569 |
| Municípios conectados intrauf | **5.566** | **5.566** |
| Municípios sem vizinhos intrauf | 3 | 3 |
| UFs com pelo menos uma aresta interna | 26 | 26 |

Os isolados intrauf são os códigos IBGE `2605459`, `3520400` e `5300108`. Brasília/DF (`5300108`) não dispõe de outro município **dentro da mesma UF**; por definição, entra como isolada neste teste. Isso não implica ausência de dados eleitorais, apenas impossibilidade de compor uma aresta intrauf.

## Moran I condicional e testes por permutação

| Resíduos de comparecimento | Queen I | Queen p bilateral | Rook I | Rook p bilateral |
| --- | ---: | ---: | ---: | ---: |
| Persistência histórica (2022 como baseline para 2026) | **0,269153** | 0,002 | **0,271008** | 0,002 |
| Ridge (Censo IBGE 2022) | **0,284911** | 0,002 | **0,286485** | 0,002 |
| Ridge + correção regional de treino | **0,284911** | 0,002 | **0,286485** | 0,002 |

A resolução mínima de p com 499 permutações e correção +1 é **0,002**. O teste produz evidência de associação espacial positiva nos resíduos intrauf para todos os modelos, condicionalmente ao embaralhamento escolhido. Os seis testes são correlacionados, exploratórios e **não** receberam ajuste de multiplicidade; sua interpretação não é causal.

A média nula condicional simulada da ridge foi **−0,005336** (*queen*) e **−0,005329** (*rook*), com intervalos percentílicos centrais de 95% de aproximadamente **[−0,02189; +0,00990]** e **[−0,02206; +0,01101]**, respectivamente. Os Moran observados estão muito acima dessas bandas.

### Por que ridge e ridge regional ficaram idênticos?

A correção regional da E007 adiciona ao erro de todos os municípios de determinada UF **o mesmo deslocamento constante**, calculado a partir da macrorregião de treinamento. Se `e'_i = e_i - c_{UF}`, então:

`e'_i - média_UF(e') = e_i - média_UF(e)`.

Assim, a autocorrelação dos **resíduos já centrados na UF** é rigorosamente invariante a essa correção. Isso explica a igualdade numérica sem implicar que os dois modelos sejam equivalentes em MAE; o intercepto regional pode melhorar erro e viés médio, mas não remove os contrastes intrauf.

## Questão de proveniência encontrada em 2026-10-18

O ZIP *live* de cruzamento de códigos TSE–IBGE foi novamente recuperado na primeira execução, porém seu SHA256 **não correspondia mais** ao snapshot auditado na E004 (hash E004 `68328ddc166806594a2aab5809ac9aa602153535d6b8a71e886c337f9f3631ca`). O pipeline bloqueou a troca da fonte. Como a E009 precisa somente dos **códigos IBGE já fixados no painel E005 auditado por SHA256**, o download redundante foi retirado; **nenhuma reatribuição silenciosa de município foi feita**. Um protocolo de migração de versões deve comparar separadamente os dois cruzamentos antes de atualizar o painel histórico.

## Significado científico e próximos experimentos

**Resultado central:** a estrutura residual não é inteiramente explicável por um intercepto médio de UF ou macrorregião; há autocorrelação espacial positiva **dentro** de estados. Isso justifica estudar estrutura local de erros e covariáveis territoriais omitidas, preservando validação geográfica fora da amostra.

**Limites:** autocorrelação residual não é causalidade; a permutação condicional não modela todas as formas de heterogeneidade local; os dados são retrospectivos; nenhuma inferência sobre bairros residenciais, eleitores individuais ou apoio futuro a candidaturas é produzida.

**Próxima etapa proposta (E010):** construir baselines espaciais estritamente *train-only* (por exemplo, regressão espacial com características disponíveis antes da eleição e validação geográfica em blocos), distinguir erro preditivo de autocorrelação residual e avaliar sensibilidade a vizinhanças, sem vazamento de resultados de municípios/estados reservados para teste. A hipótese deve ser congelada antes de qualquer comparação confirmatória.

### Reprodutibilidade

Arquivos: `src/electoral_analysis/state_conditional_moran.py`, `src/electoral_analysis/conditional_moran_figure.py`, `tests/test_state_conditional_moran.py`, `tests/test_conditional_moran_figure.py`, `docs/e009_protocol.md` e `.github/workflows/e009-state-conditioned.yml`.
