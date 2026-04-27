# Scraping

O scraping do projeto é centrado em LinkedIn e segue o contrato de adapter tradicional:

- `fetch(url)`
- `extract(raw_page)`
- `normalize(payload, request)`

## Componentes

- `fetcher.py`: navegação com Playwright
- `extractor.py`: leitura de DOM e fallback de seletores
- `selectors.py`: estratégia resiliente de busca
- `adapter.py`: integração entre fetch, extract e normalize

## Boas práticas adotadas

- URL canônica para deduplicação
- limpeza de ruído em título e localização
- detecção de vagas fechadas
- captura de vagas relacionadas

## Reuso de sessão no lote por CSV

Para a importação em lote, o fluxo de scraping foi ajustado para suportar reuso da sessão do navegador.

Em vez de abrir e fechar Playwright para cada URL, o lote:

1. abre uma sessão do LinkedIn uma única vez
2. navega por várias URLs na mesma sessão
3. processa uma vaga por vez
4. fecha a sessão ao final do lote

## Por que o lote é sequencial

A estratégia atual é propositalmente sequencial, mesmo em batch, para reduzir risco operacional:

- menos chance de conflito de sessão
- menor probabilidade de bloqueio pelo site
- debugging mais simples
- melhor rastreabilidade de erro por item

Ou seja: o ganho vem de reusar a sessão, não de paralelizar submissões.
