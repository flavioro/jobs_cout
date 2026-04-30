# Architecture

## Camadas principais

### 1. Scraping

`src/adapters/linkedin` concentra fetch, extract e normalize para vagas do LinkedIn.

Componentes relevantes:

- `fetcher.py`: navegação em vaga individual com Playwright;
- `extractor.py`: extração de detalhes da vaga individual;
- `adapter.py`: integra fetch/extract/normalize para o fluxo de ingestão por URL;
- `search_fetcher.py`: navegação em páginas de busca, scroll incremental e abertura de detalhes;
- `search_extractor.py`: extração dos cards da busca;
- `search_selectors.py`: seletores/fallbacks para a busca.

### 2. Application services

`src/services` orquestra ingestão, enriquecimento, persistência e staging.

Serviços principais:

- `ingest_service.py`: fluxo de ingestão de URL individual para `jobs`;
- `linkedin_search_collection_service.py`: coleta vagas de buscas do LinkedIn;
- `linkedin_search_ingest_service.py`: coleta e ingestão direta em `jobs`;
- `job_candidate_service.py`: staging/fila `job_candidates` e processamento posterior;
- `persistence_service.py`: persistência/deduplicação da tabela `jobs`.

### 3. Staging/fila de candidatos

A tabela `job_candidates` separa a coleta da criação final de `Job`.

Fluxo recomendado:

```text
LinkedIn Search
→ search_fetcher/search_extractor
→ LinkedInSearchJobCard
→ job_candidate_service.upsert_job_candidates
→ job_candidates.processing_status = pending/skipped
→ process_job_candidates
→ ingest_service
→ jobs
→ job_candidates.processing_status = processed/failed/skipped
```

Essa camada permite:

- auditar vagas coletadas;
- evitar duplicação;
- reprocessar falhas;
- manter histórico de vagas fechadas;
- controlar quando uma vaga coletada vira `Job`.

### 4. Browser AI

`src/adapters/ai_web` concentra integrações web para ChatGPT e Gemini.

Essa camada foi isolada do scraping porque lida com um domínio diferente: automação de conversas, perfis persistentes, retries, seletores e captura de resposta.

Cada provider segue o mesmo contrato:

- `AIChatOptions`: modo de execução e timeout;
- `AIResponse`: saída estruturada;
- `BaseAIWebFetcher`: navegação, retry, debug e extração incremental;
- `BaseAIWebAdapter`: persistência do log e interface padronizada.

### 5. API

`src/api` expõe os endpoints FastAPI.

Endpoints relevantes para a busca do LinkedIn:

```text
POST /linkedin/search-jobs/collect-ingest
POST /linkedin/search-jobs/collect-candidates
GET  /job-candidates
POST /job-candidates/process
```

### 6. Data layer

`src/db` define modelos, base e sessão.

Tabelas principais:

- `jobs`: vagas finais;
- `job_candidates`: staging/fila de vagas coletadas;
- `related_jobs`: vagas relacionadas capturadas em páginas individuais;
- `blocked_jobs`: registros bloqueados por regra de negócio.

## Desenho dos fluxos

### Ingestão por URL individual

```text
URL LinkedIn
→ AdapterFactory
→ LinkedInAdapter
→ fetch página individual
→ LinkedInExtractor
→ normalize
→ upsert_job
→ jobs/related_jobs/blocked_jobs
```

### Busca com auditoria

```text
URLs de busca
→ SearchFetcher
→ SearchExtractor
→ cards deduplicados
→ Excel/HTML/PNG
```

### Busca com staging

```text
URLs de busca
→ SearchFetcher
→ SearchExtractor
→ cards deduplicados
→ job_candidates
```

### Processamento da staging

```text
job_candidates pending/failed
→ process_job_candidates
→ ingest_service com adapter/fetcher reaproveitado
→ jobs
→ marca candidate como processed/skipped/failed
```

## Chat mode

- `new_chat`: abre o app base e tenta iniciar um chat limpo;
- `existing_chat`: abre uma URL específica de conversa.

`new_chat` é o modo recomendado para testes determinísticos.

## Observabilidade

Cada execução pode salvar:

- HTML final em `data/debug/`;
- screenshot em `data/debug/`;
- Excel de auditoria em `data/exports/`;
- log de respostas AI em `data/ai_responses_log.json`.

Esses arquivos são artefatos locais e não devem ser commitados.

## Migração de banco

O projeto usa `migrate_db.py` para ajustes incrementais no SQLite local. Para a staging queue, esse script deve garantir a criação da tabela `job_candidates` e os índices principais, preservando dados existentes.

Comando recomendado:

```bash
python migrate_db.py
```
