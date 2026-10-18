# E011 — Atlas Eleitoral Municipal

Esta aplicação estática exibe **estatísticas eleitorais históricas agregadas** de 2022 e 2026, para todas as candidaturas presidenciais, sem prever eleições futuras ou atribuir preferências individuais.

## Conteúdo

- 5.570 municípios, reconciliados com códigos do IBGE.
- Primeiro turno de 2022 e 2026, seleção por UF, ano e candidatura.
- Comparecimento, variação das taxas, votos válidos, brancos e nulos.
- Polígonos do IBGE 2022 com geometrias simplificadas **somente para visualização**.
- Uma ressalva explícita sobre o denominador municipal de 2022 no Amazonas.
- Sem cookies, telemetria, classificação de municípios por persuadibilidade ou inferência de bairros residenciais.

## Construção e reprodutibilidade

O workflow E011 recupera o painel E005 (SHA256 fixado) e a malha municipal IBGE 2022 (SHA256 fixado), executa os testes e gera a pasta docs/atlas com arquivos estáticos. O ZIP de origem, dados pessoais e saídas de modelos de voto não são incorporados ao site.

O CI publica um artefato ZIP de visualização e versiona os arquivos gerados na branch do PR. A compilação falha caso existam problemas de correspondência municipal, votos de candidatura que não somam os votos válidos, geometrias ausentes ou hashes inesperados.

## Executar localmente

Depois de gerar ou baixar docs/atlas, execute o comando:

    python -m http.server 8000 --directory docs/atlas

Acesse http://localhost:8000. Não abra o HTML diretamente via file:// porque o navegador pode impedir leituras fetch() locais.

## GitHub Pages

Depois de incorporar o PR consolidado na main, selecione Settings → Pages → Deploy from a branch → main /docs. O caminho esperado será /atlas/ no site Pages do projeto, mas a URL não deve ser anunciada como ativa sem verificar a publicação.

## Denominadores e interpretação

- Participação de candidatura: votos nominais daquela candidatura divididos por votos válidos registrados no município/ano.
- Brancos e nulos: votos da categoria divididos pelo comparecimento.
- Comparecimento: comparecimento dividido pelos eleitores aptos nas seções regulares.
- Variação no comparecimento: diferença entre taxas agregadas de 2026 e 2022; não é a migração de indivíduos.
- Local de votação não informa necessariamente município ou bairro de residência.

Fontes: Portal de Dados Abertos do TSE e Malha Municipal Digital do IBGE 2022, com hashes e contagens dentro do manifesto do atlas.
