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
