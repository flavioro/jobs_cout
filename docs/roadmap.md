# Roadmap

## Concluído

### LinkedIn individual ingest

- ingestão de vaga por URL;
- normalização e deduplicação;
- blocklist;
- captura de `related_jobs`;
- testes unitários e regressão com páginas reais.

### Browser AI providers

- contrato único para provedores web;
- ChatGPT web;
- Gemini web;
- logs estruturados;
- retries e screenshots/HTML de debug.

### CSV batch import

- leitura de CSV;
- ingestão em lote;
- filtros de status;
- scripts PowerShell auxiliares.

### LinkedIn Search collect/ingest

- login LinkedIn persistente;
- coleta de cards de busca;
- scroll incremental;
- dedup por `linkedin_job_id`/URL;
- Excel de auditoria;
- detecção de vagas fechadas;
- preenchimento de cards parciais usando o extrator do fluxo `ingest-url`;
- ingestão direta opcional com `--ingest`.

### JobCandidate staging queue

- tabela `job_candidates`;
- coleta com `--save-candidates`;
- processamento posterior com `scripts.process_job_candidates`;
- status `pending`, `processed`, `failed`, `skipped`;
- migração em `migrate_db.py`;
- endpoints para coletar/listar/processar candidatos;
- testes unitários;
- validação real no SQLite.

## Próximo curto prazo

- documentar consultas úteis para analisar `job_candidates` por status;
- adicionar relatório/resumo operacional da fila;
- melhorar saída do script `process_job_candidates` com contadores por status;
- adicionar opção de reprocessamento seletivo por `source_search_url`;
- melhorar filtros em `GET /job-candidates`.

## Médio prazo

- priorização/score antes de virar `Job`;
- enriquecimento IA depois da staging queue;
- tela ou endpoint operacional para revisar candidatos;
- métricas de performance por etapa;
- workers assíncronos para processamento recorrente;
- suporte a múltiplas fontes de vagas além do LinkedIn.

## Longo prazo

- dashboard operacional de ingestão/enrichment;
- agendamento de buscas recorrentes;
- fila robusta com retries/backoff;
- automações orientadas por perfil e prioridade de candidatura;
- múltiplos providers de busca e enriquecimento.
