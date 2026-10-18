# E010 — Histórico dos vizinhos como variável espacial: avaliação retrospectiva

**Data:** 2026-10-18. **Estado:** experimento completo sobre fontes oficiais SHA256-fixadas; workflow aprovado, 62 testes e Ruff aprovados. **Escopo:** comparecimento eleitoral municipal, sem estimativa de escolha eleitoral, votos em Lula ou propensão à persuasão.

## Questão e implementação previamente especificadas

Após a E009 demonstrar autocorrelação intrauf positiva nos resíduos do comparecimento, a E010 perguntou se adicionar a **média da taxa de comparecimento de municípios vizinhos de 2022** aos preditores da ridge permitiria reduzir erro de generalização em 2026.

Conforme [protocolo E010](../../docs/e010_protocol.md), a informação espacial usada na predição de 2026 é calculada **somente** a partir da geometria IBGE 2022 e das taxas observadas em **2022**; não usa comparecimento, erros ou votos em candidaturas em 2026 como features. Comparou-se a ridge comum de três variáveis, a correção regional E007, e modelos de quatro variáveis usando vizinhos queen ou rook. As padronizações e coeficientes foram aprendidos **exclusivamente com municípios dos estados de treino** em 27 rodadas leave-one-UF-out. Penalização ridge: 10 (fixa). Para dois municípios insulares sem vizinhos na malha, a média histórica foi definida como a própria taxa de 2022, com contabilização explícita.

## Fontes e reprodutibilidade

- [GitHub Actions E010: execução 39132449606](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39132449606) — **success**; 62 testes aprovados, Ruff aprovado.
- [JSON completo e diagnósticos](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39132449606/artifacts/12138363277), retenção temporária de 14 dias.
- Fontes: painel municipal eleitoral TSE E005 (SHA256 `2b84fd89497c10a9d47f6a1a1793da144ac1be845df97605101607e424e1323d`), Censo IBGE 2022 E006 (`145bd9448282278e3de4290bf1e26e025bc783965defb6f82c71be467439b641`) e Malha Municipal IBGE 2022 (`9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2`).
- **5.569 municípios**, 27 rodadas de teste por UF e mesma amostra em todos os cinco modelos. Os 2 municípios sem ligações na malha são `2605459` e `3520400`. A exceção do Amazonas E005/E006 segue explicitamente excluída dessa comparação.
- Os MAEs anteriores da ridge E006 e da ridge corrigida E007 foram reproduzidos com tolerância `10⁻⁸` antes da avaliação espacial.

## Principais resultados: erro de comparecimento (pontos percentuais)

| Modelo | MAE | RMSE |
| --- | ---: | ---: |
| Persistência histórica 2022 | 2,135508 | 2,857657 |
| Ridge E006 | 1,956734 | 2,502372 |
| **Ridge + intercepto regional E007** | **1,791499** | **2,286228** |
| Ridge + média histórica queen 2022 | 1,945454 | 2,482146 |
| Ridge + média histórica rook 2022 | 1,945274 | 2,482016 |

**Conclusão negativa:** o modelo de quatro features melhorou apenas **0,0113–0,0115 pp** em MAE em relação à ridge convencional. Entretanto, em comparação à correção regional E007, os modelos queen e rook **aumentaram** o erro em **+0,153955 pp** e **+0,153774 pp**, respectivamente. Em proporção ao MAE E007, isso representa uma deterioração de aproximadamente **8,6%**.

### Sensibilidade por bootstrap de UFs

Comparação: **MAE espacial menos MAE E007**. Quatrocentas amostragens de estados com reposição; semente 2718, usando tamanho efetivo variável dos grupos.

| Modelo espacial | Diferença média | Intervalo percentílico exploratório 95% |
| --- | ---: | --- |
| Queen histórica 2022 | +0,153955 pp | **[+0,029222; +0,293481] pp** |
| Rook histórica 2022 | +0,153774 pp | **[+0,026285; +0,283636] pp** |

Os intervalos permanecem positivos neste protocolo, sugerindo que a inferioridade em relação à E007 é relativamente estável à reamostragem das UFs. Mas o desenho, selecionado depois de observar E009, continua sendo **exploratório e retrospectivo**; os intervalos não substituem validação independente em outra eleição.

## A autocorrelação espacial desapareceu?

Não. Usando a definição **E009** (centralização por UF e permutação restrita a UF), obtivemos:

| Vetor residual | Moran queen condicional | Moran rook condicional |
| --- | ---: | ---: |
| Ridge E006 | 0,284911 | 0,286485 |
| Ridge regional E007 | 0,284911 | 0,286485 |
| **Ridge espacial histórica E010** | **0,284323** | **0,285999** |

Cada conjunto utiliza **5.566 nós conectados** e 499 permutações intraestadual. Os p-valores bilaterais observados foram `0,002` (piso com 499 permutações) para os vetores espaciais. A diminuição condicional foi de cerca de **−0,000588** (queen) e **−0,000486** (rook), sem mudança material da estrutura residual positiva.

A correção regional não altera Moran centrado por UF porque ela adiciona um deslocamento constante aos resíduos dessa UF. Os testes queen e rook seguem produzindo conclusões semelhantes. **Detectar autocorrelação residual não garante que um preditor de defasagem histórica simples captura o processo que gera os resíduos.**

## Restrições interpretativas

- Esta é uma avaliação retrospectiva com treino em resultados de 2026 de outras UFs e teste num estado reservado; **não é previsão prospectiva disponível em 2022**. As datas de publicação dos dados do Censo 2022 também limitam afirmações de disponibilidade ex-ante.
- O experimento foi desenhado após resultados E009; não existe período eleitoral independente de validação confirmatória. A escolha da variante queen vs rook não pode ser guiada pelo menor erro observado.
- A autocorrelação não prova causalidade entre vizinhos. Deslocamentos regionais, composição do eleitorado e covariáveis omitidas exigem avaliação própria.
- Taxas de comparecimento não identificam a opção de voto de nenhum eleitor. Não é um modelo de votos futuros para Lula ou qualquer candidato e não fornece estimativas de potencial de persuasão municipal ou por bairro.

## Próxima decisão metodológica

**Não promover automaticamente o lag espacial simples como modelo principal.** Manter E007 como benchmark empírico de menor erro e implementar, numa E011 separada e com hipótese fixada, uma investigação de *efeitos locais não observados* e avaliação espacial mais severa, incluindo um teste fora da amostra temporal que dependa de dados efetivamente disponíveis no momento da previsão. Antes de introduzir modelos espaciais de maior complexidade, especificar claramente o mecanismo hipotetizado, a matriz de pesos, os mecanismos de extrapolação a novos estados e a regularização, sem ajuste em dados de teste.
