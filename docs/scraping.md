# Scraping

O scraping do projeto é centrado em LinkedIn e segue o contrato de adapter tradicional:

- `fetch(url)`
- `extract(raw_page)`
- `normalize(payload, request)`

## Componentes de vaga individual

- `fetcher.py`: navegação com Playwright
- `extractor.py`: leitura de DOM e fallback de seletores
- `selectors.py`: estratégia resiliente de busca
- `adapter.py`: integração entre fetch, extract e normalize

## Componentes de busca LinkedIn

- `search_selectors.py`: seletores e textos usados na página de busca
- `search_extractor.py`: normalização dos cards da busca
- `search_fetcher.py`: abertura da busca, scroll incremental, extração de cards e abertura de URLs individuais quando necessário

## Fluxo da busca LinkedIn

```text
URL de busca LinkedIn
→ abre com profile persistente
→ espera renderização inicial
→ coleta cards visíveis
→ rola a lista lateral
→ coleta novamente
→ deduplica por job_id/url
→ completa cards parciais pela URL individual
→ exporta Excel/HTML/PNG
```

## Scroll incremental

O LinkedIn virtualiza a lista de vagas. Por isso o projeto não espera a página inteira carregar.

A estratégia é:

1. extrair os cards atualmente visíveis
2. rolar o container lateral de resultados
3. aguardar curto intervalo
4. extrair de novo
5. mesclar os cards por `linkedin_job_id` ou URL
6. parar quando atingir o limite ou quando não aparecerem cards novos por algumas rodadas

## Cards completos, parciais e fechados

A coleta classifica cards em:

- `complete`: possui dados mínimos úteis
- `partial`: possui URL, mas faltam campos como título, empresa ou localização
- `closed`: vaga expirada ou sem aceitar candidaturas
- `invalid`: sem dados mínimos para uso

Cards parciais são preservados, porque uma URL parcial ainda pode ser completada abrindo a vaga individual.

## Complemento de cards parciais

Quando um card tem URL mas faltam campos, o fetcher abre a URL individual da vaga e reutiliza o extractor do fluxo de `ingest-url`.

Isso evita manter dois parsers completos diferentes para a página de vaga.

## Vagas fechadas/expiradas

O projeto detecta termos como:

- `Expirado`
- `Vaga expirada`
- `Não aceita mais candidaturas`
- `Candidaturas encerradas`
- `No longer accepting applications`
- `Job expired`

Por padrão, vagas fechadas aparecem no Excel para auditoria, mas são ignoradas na ingestão.

## Artefatos de debug

A coleta salva artefatos para inspeção manual:

- HTML da busca em `data/debug/`
- screenshot da busca em `data/debug/`
- Excel de auditoria em `data/exports/linkedin_search_cards.xlsx`

Esses arquivos não devem ser versionados.

## Boas práticas adotadas

- URL canônica para deduplicação
- limpeza de ruído em título e localização
- detecção de vagas fechadas
- preservação de links parciais
- preferência por cards mais ricos quando o mesmo job aparece mais de uma vez
- reutilização do extractor de `ingest-url` para páginas individuais
- separação entre modo auditoria e modo ingestão
