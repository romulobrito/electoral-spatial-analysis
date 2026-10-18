# E008 — Autocorrelação espacial dos resíduos de comparecimento municipal

**Data:** 17 de outubro de 2026. **Situação:** execução nacional com dados oficiais concluída, CI aprovado (**51 testes**, Ruff sem erros). **Escopo:** comparecimento eleitoral agregado, sem perfis individuais ou escores de voto/persuasão por candidatura.

## Fontes e auditoria de geometrias

- [Malha Municipal Digital IBGE 2022](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/) `BR_Municipios_2022.zip`; SHA256 `9c904fa1feb978a89042bfecd7758e571266f285d6122a4ff02ffe37bffb76a2`; 203.627.589 bytes; 5.572 geometrias com referência **SIRGAS 2000 / EPSG:4674**.
- [Execução integral E008 GitHub Actions 39080729939](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39080729939), [artefatos JSON e SVG](https://github.com/romulobrito/electoral-spatial-analysis/actions/runs/39080729939/artifacts/12118449463), retenção de 14 dias.
- Resíduos `out-of-state` reconstruídos exatamente da E007 com painel eleitoral TSE E005 e Censo IBGE E006, fonte e chaves geográficas conferidas por hashes fixados. O cálculo reproduziu o MAE anterior com tolerância de 10⁻⁸.
- Os códigos IBGE **4300001** e **4300002** representam as áreas estaduais operacionais que não são municípios eleitorais; código **1302603** foi excluído da comparação de modelos pela exceção ainda não regularizada do denominador 2022 no Amazonas. Isso deixa **5.569 municípios** analisáveis.

## Grafos territoriais e isolamento

Vizinhos *queen* são polígonos cujo contorno se toca, inclusive num vértice. Vizinhos *rook* compartilham trecho de fronteira de comprimento positivo, usando a malha original **sem simplificação**. As arestas não são direcionadas; para Moran, as linhas são padronizadas para soma de pesos unitária.

| Indicador | Queen | Rook |
|---|---:|---:|
| Municípios com geometrias | 5.569 | 5.569 |
| Arestas únicas | **16.455** | **15.986** |
| Geometrias sem vizinhos | **2** | **2** |
| Nós efetivos no cálculo | **5.567** | **5.567** |
| Grau médio, sem isolados | 5,912 | 5,743 |
| Grau máximo | 23 | 21 |

Os municípios isolados em ambos os grafos possuem os códigos IBGE **2605459** e **3520400**. Eles não são imputados e não entram no denominador de Moran. Por serem desconectados na malha, sua exclusão **não** indica ausência de dados eleitorais.

## Moran I global observado

| Vetor de resíduos de comparecimento | Queen | Rook |
|---|---:|---:|
| Persistência da taxa de 2022 | **+0,4683** | **+0,4689** |
| Ridge com Censo 2022 | **+0,4973** | **+0,4982** |
| Ridge + correção macrorregional (E007) | **+0,3959** | **+0,3968** |

Cada configuração recebeu **499 permutações** com semente 2718. O teste bilateral retornou **p=0,002** em todos os seis casos (menor resolução possível com 499 permutações). A hipótese nula condicional é um embaralhamento global dos resíduos sobre a malha fixa; **não** foi testado um embaralhamento restrito a UF e nem foi aplicada correção por múltiplos testes. Os p-valores são **exploratórios**.

### Interpretação

1. Todos os vetores apresentam autocorrelação positiva substantiva. Os erros tendem a se parecer com os de municípios geograficamente próximos, de acordo com a topologia do IBGE.
2. A ridge comum reduziu o MAE global contra a persistência, mas **aumentou Moran I** (0,4683 → 0,4973 sob queen). Melhor MAE não significa resíduos espacialmente independentes.
3. A correção macrorregional reduziu Moran I da ridge de 0,4973 para 0,3959 (queen), uma diferença de aproximadamente **−0,1014** em I; ainda sobra dependência espacial relevante.
4. As conclusões numéricas globais são muito semelhantes entre queen e rook, sugerindo que o resultado não depende fortemente de contatos por vértice na malha de 2022.
5. Os resultados não autorizam inferir causalidade da geografia, preferência política individual, bairro de residência, probabilidade de voto futuro ou alvos de campanha.

## Limitações e próximos controles

- O teste de permutação global pode detectar diferenças entre estados/regiões que contribuem para vizinhança aparente. A próxima hipótese útil é calcular Moran sobre **resíduos centrados por UF** e realizar **permutações condicionadas aos estados**, mantendo o desenho de validação para distinguir dependência fina de heterogeneidade administrativa.
- O método macrorregional surgiu após a E006. Nenhum teste nesta E008 é confirmatório independente em outra eleição.
- Dois polígonos municipais isolados foram excluídos apenas do cálculo com pesos de contiguidade, não de estimativas populacionais/eleitorais.
- A leitura da seção de votação não revela bairro de residência; o dado mais detalhado requer outra fonte e método de compatibilização.
- Não houve avaliação de uma previsão de votos por candidatura.

## Arquivos reproduzíveis

- `src/electoral_analysis/spatial_moran.py`: reconciliação dos erros held-out, construção de vizinhos e Moran por permutação.
- `src/electoral_analysis/spatial_figure.py`: figura vetorial com os indicadores.
- `tests/test_spatial_moran.py`, `tests/test_spatial_figure.py`: verificações com grafos sintéticos.
- `docs/e008_spatial_protocol.md`: definições e hipóteses.
- `.github/workflows/e008-moran.yml`: reprodução com origem, hashes e checks automatizados.

**Resumo:** a E008 demonstra correlação espacial residual não eliminada pela regressão ridge ou pela correção macrorregional. Para afirmar dependência além dos efeitos de estado, ainda é necessário o teste condicional explicitado acima.
