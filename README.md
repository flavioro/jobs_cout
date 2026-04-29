# Job Scout

Job Scout é um pipeline para ingestão de vagas do LinkedIn, enriquecimento por IA e automação opcional de provedores web como ChatGPT e Gemini.

## Visão geral

O projeto combina cinco frentes principais:

- scraping resiliente de vagas do LinkedIn via Playwright
- coleta de vagas a partir de páginas de busca do LinkedIn
- ingestão individual, por CSV e por busca do LinkedIn
- enriquecimento estruturado por IA para fit, skills, inglês, senioridade e setor
- automação web opcional para provedores conversacionais com perfil persistente

## Quick start

1. Crie e ative seu ambiente virtual.
2. Instale as dependências com `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e ajuste as variáveis.
4. Rode a API com `uvicorn src.main:app --reload`.
5. Rode os testes com `pytest` ou com os scripts PowerShell do projeto.

## Features

- ingestão de vagas por URL do LinkedIn
- importação em lote por CSV com filtro por status
- coleta de vagas por URLs de busca do LinkedIn
- modo de auditoria com exportação Excel, HTML e screenshot
- modo de ingestão real das vagas coletadas na tabela `Job`
- normalização, deduplicação e blocklist por título
- persistência em SQLite com SQLAlchemy assíncrono
- enriquecimento por provider configurável:
  - `groq`
  - `chatgpt_web`
  - `gemini_web`
- automação web para ChatGPT e Gemini com chat novo ou chat existente por URL
- logging de respostas de browser AI em JSON lines

## Comandos principais

### API

```bash
uvicorn src.main:app --reload
```

### Ingestão de uma vaga por URL

Use o endpoint `POST /ingest-url`.

### Coleta de vagas por busca do LinkedIn

Somente coleta e auditoria:

```bash
python -m scripts.collect_linkedin_search_jobs
```

Coleta e simulação de ingestão, sem gravar no banco:

```bash
python -m scripts.collect_linkedin_search_jobs --ingest --dry-run
```

Coleta e gravação real na tabela `Job`:

```bash
python -m scripts.collect_linkedin_search_jobs --ingest
```

Login persistente no LinkedIn:

```bash
python -m scripts.login_linkedin
```

## Arquitetura

Em alto nível, o projeto é dividido em:

- `src/adapters/linkedin`: coleta e extração de vagas
- `src/services`: orquestração de ingestão, persistência e enrichment
- `src/adapters/ai_web`: automação web de provedores de IA
- `src/api`: endpoints FastAPI
- `src/db`: modelos e sessão do banco

Mais detalhes estão em `docs/architecture.md`.

## Documentação detalhada

- `docs/architecture.md`
- `docs/enrichment.md`
- `docs/scraping.md`
- `docs/csv-import.md`
- `docs/web-enrichment.md`
- `docs/linkedin-search.md`
- `docs/roadmap.md`

## Testes

Unitários e integração:

```bash
pytest
```

Testes focados da busca LinkedIn:

```bash
pytest -q tests/test_linkedin_search_extractor.py tests/test_linkedin_search_collection_service.py tests/test_linkedin_search_fetcher_scroll.py tests/test_linkedin_search_ingest_service.py tests/test_routes_linkedin_search_collect.py
```

Smoke manual para providers:

```bash
python -m scripts.manual_chatgpt_check
python -m scripts.manual_gemini_check
```

## Observações sobre browser AI

O modo padrão é `new_chat`, mais previsível para automação.

No enrichment web, o projeto aplica:

- prompt estruturado pedindo JSON
- extração do primeiro objeto JSON da resposta
- normalização defensiva de campos como `sector`, `english_level` e `seniority_suggestion`
- validação Pydantic antes de persistir

O modo `existing_chat` é suportado via URL configurável, mas traz risco maior de contaminação de contexto.
