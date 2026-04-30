# Scraping

O scraping do projeto é centrado em LinkedIn e segue dois fluxos complementares:

1. scraping de uma vaga individual;
2. scraping de páginas de busca com múltiplos cards.

## Scraping de vaga individual

Contrato tradicional do adapter:

```text
fetch(url)
extract(raw_page)
normalize(payload, request)
```

Componentes:

- `fetcher.py`: navegação com Playwright;
- `extractor.py`: leitura de DOM e fallback de seletores;
- `selectors.py`: estratégia resiliente para página individual;
- `adapter.py`: integração entre fetch, extract e normalize.

Esse fluxo alimenta diretamente a tabela `jobs` e pode capturar `related_jobs`.

## Scraping de busca LinkedIn

O scraping de busca abre URLs de resultado do LinkedIn e captura cards.

Componentes:

- `search_fetcher.py`: abre a busca, faz scroll incremental, coleta cards visíveis e abre detalhes quando necessário;
- `search_extractor.py`: transforma DOM/payload do browser em cards estruturados;
- `search_selectors.py`: concentra seletores e fallbacks da página de busca;
- `linkedin_search_collection_service.py`: orquestra coleta, deduplicação e exportação;
- `job_candidate_service.py`: salva cards coletados em `job_candidates`.

## Fluxo recomendado atual

```text
LinkedIn Search URL
→ scroll incremental
→ captura cards
→ dedup por linkedin_job_id/URL
→ completa parciais com página individual
→ grava/atualiza job_candidates
→ processa candidatos para jobs em etapa separada
```

## Boas práticas adotadas

- URL canônica para deduplicação;
- deduplicação por `linkedin_job_id` quando disponível;
- limpeza de ruído em título e localização;
- detecção de vagas fechadas/expiradas;
- captura de vagas relacionadas no fluxo individual;
- exportação opcional de Excel para auditoria;
- staging table para não depender de Excel como fonte de verdade.

## Comandos úteis

Coletar busca apenas para auditoria:

```bash
python -m scripts.collect_linkedin_search_jobs
```

Coletar busca e salvar na staging table:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates
```

Coletar sem Excel:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates --no-export-xlsx
```

Processar staging para `jobs`:

```bash
python -m scripts.process_job_candidates --dry-run --limit 20
python -m scripts.process_job_candidates --limit 20
```

## Vagas fechadas

Vagas fechadas/expiradas devem ser registradas em `job_candidates`, mas normalmente marcadas como `skipped` no processamento.

Isso preserva auditoria sem poluir a tabela `jobs`.

## Arquivos locais gerados

O scraping pode gerar:

```text
data/debug/*.html
data/debug/*.png
data/exports/*.xlsx
data/linkedin_profile/
data/jobscout.db
```

Esses arquivos não devem ser commitados.
