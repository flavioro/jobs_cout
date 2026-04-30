# LinkedIn Search

Este documento descreve o fluxo de coleta de vagas a partir de páginas de busca do LinkedIn e o fluxo novo de staging com a tabela `job_candidates`.

## Objetivo

O fluxo LinkedIn Search permite sair de uma URL de busca, capturar vários cards de vagas, completar dados ausentes, salvar os resultados em uma tabela intermediária e depois transformar esses candidatos em registros finais na tabela `jobs`.

O fluxo recomendado atual é:

```text
LinkedIn Search URL
→ coleta de cards com scroll incremental
→ deduplicação por linkedin_job_id/URL
→ preenchimento de cards parciais via página individual
→ gravação/atualização em job_candidates
→ processamento posterior para jobs
→ marcação do candidato como processed/skipped/failed
```

## Por que existe `job_candidates`

Antes, a busca podia gerar Excel e/ou ingerir diretamente em `jobs`. Agora existe uma etapa intermediária para controlar melhor o pipeline.

Vantagens:

- separa coleta de processamento;
- evita perder vagas quando uma etapa posterior falha;
- permite auditar tudo que foi encontrado;
- permite reprocessar falhas;
- evita gastar processamento/IA com vagas ruins ou fechadas;
- mantém histórico de vagas fechadas/expiradas encontradas nas buscas;
- permite priorizar candidatos antes de virarem `Job`.

## Tabela `job_candidates`

A tabela `job_candidates` funciona como staging table/fila de processamento.

Campos conceituais principais:

```text
id
source
source_job_id
source_url
source_search_url

title
company
location_raw
workplace_type
employment_type
seniority_hint
is_easy_apply

availability_status
availability_reason
extraction_status
missing_fields

raw_card_text
raw_detail_text
raw_payload_json

processing_status
processing_attempts
processing_error

job_id
processed_at
collected_at
created_at
updated_at
```

## Identidade e deduplicação

A deduplicação deve priorizar:

```text
1. source + source_job_id
2. source_url/canonical_url
3. fallback fraco: title + company + location
```

Para LinkedIn, o melhor identificador é o `linkedin_job_id`.

Exemplo:

```text
source = linkedin
source_job_id = 4408517292
source_url = https://www.linkedin.com/jobs/view/4408517292/
```

## Status de disponibilidade

`availability_status` representa a situação da vaga no LinkedIn:

```text
open
closed
unknown
```

Exemplos de vaga fechada/expirada:

```text
Expirado
Vaga expirada
Não aceita mais candidaturas
Candidaturas encerradas
No longer accepting applications
Job expired
```

Vagas fechadas devem ser salvas em `job_candidates`, mas normalmente não devem virar `Job`.

## Status de extração

`extraction_status` representa a qualidade do card extraído:

```text
complete
partial
closed
invalid
```

Cards parciais podem ser completados abrindo a URL individual da vaga e reaproveitando o extrator já usado pelo fluxo `POST /ingest-url`.

## Status de processamento

`processing_status` representa a etapa da fila:

```text
pending
processing
processed
failed
skipped
```

Fluxos possíveis:

```text
pending → processing → processed
pending → processing → failed
pending → skipped
```

Regras sugeridas:

```text
vaga aberta e válida → pending
vaga fechada/expirada → skipped
sem URL válida → skipped
erro de ingestão → failed
vaga criada/atualizada em jobs → processed
```

## Preparar banco

Antes de usar o fluxo novo no banco local, execute:

```bash
python migrate_db.py
```

Esse script garante as colunas antigas necessárias e cria a tabela `job_candidates` quando ainda não existir.

## Login persistente

Antes de coletar vagas, faça login no LinkedIn:

```bash
python -m scripts.login_linkedin
```

O profile persistente evita login manual a cada execução.

Configuração relacionada:

```python
linkedin_profile_path = "data/linkedin_profile"
```

## Arquivo de URLs de busca

Arquivo padrão:

```text
data/linkedin_search_urls.json
```

Formato esperado:

```json
[
  "https://www.linkedin.com/jobs/search/?keywords=Python&location=Brasil"
]
```

## Coletar somente para auditoria

Gera Excel/HTML/PNG, mas não salva candidatos e não ingere em `jobs`:

```bash
python -m scripts.collect_linkedin_search_jobs
```

## Coletar e salvar em `job_candidates`

Esse é o fluxo recomendado:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates
```

Esse comando faz:

```text
abre URLs de busca
faz scroll incremental
captura cards
completa parciais
salva/atualiza job_candidates
gera Excel de auditoria por padrão
```

Sem Excel:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates --no-export-xlsx
```

Com limite por URL:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates --max-jobs-per-url 25
```

## Processar candidatos para `jobs`

Simulação:

```bash
python -m scripts.process_job_candidates --dry-run --limit 20
```

Processamento real:

```bash
python -m scripts.process_job_candidates --limit 20
```

Reprocessar falhas:

```bash
python -m scripts.process_job_candidates --retry-failed --limit 20
```

Parar no primeiro erro:

```bash
python -m scripts.process_job_candidates --limit 20 --stop-on-error
```

## Fluxo antigo: ingestão direta

Ainda existe o modo de coleta + ingestão direta:

```bash
python -m scripts.collect_linkedin_search_jobs --ingest
```

E simulação:

```bash
python -m scripts.collect_linkedin_search_jobs --ingest --dry-run
```

Mas para operação recorrente, prefira o fluxo com `--save-candidates` + `process_job_candidates`, porque ele mantém histórico, status e reprocessamento.

## Endpoints

### Coletar e ingerir direto

```text
POST /linkedin/search-jobs/collect-ingest
```

### Coletar para candidatos

```text
POST /linkedin/search-jobs/collect-candidates
```

### Listar candidatos

```text
GET /job-candidates
```

### Processar candidatos

```text
POST /job-candidates/process
```

## Configurações principais

```python
linkedin_profile_path: str = "data/linkedin_profile"
linkedin_search_urls_path: str = "data/linkedin_search_urls.json"
linkedin_search_scroll_steps: int = 8
linkedin_search_scroll_delay_s: float = 1.5
linkedin_search_initial_wait_s: float = 2.0
linkedin_search_detail_wait_s: float = 1.5
linkedin_search_stable_scroll_rounds: int = 3
linkedin_search_card_limit_per_url: int = 25
linkedin_search_export_xlsx_enabled: bool = True
linkedin_search_export_xlsx_path: str = "data/exports/linkedin_search_cards.xlsx"
linkedin_search_skip_closed: bool = True
```

## Auditoria

Mesmo com `job_candidates`, o Excel continua útil para depuração.

Arquivo padrão:

```text
data/exports/linkedin_search_cards.xlsx
```

Arquivos de debug também podem ser gerados em `data/debug/`.

Atenção: `data/`, banco local, profiles e exports reais não devem ser commitados.

## Validação funcional recomendada

Depois de aplicar alterações na feature:

```bash
python migrate_db.py
pytest -q tests/test_job_candidate_service.py tests/test_routes_linkedin_search_collect.py
python -m scripts.collect_linkedin_search_jobs --save-candidates
python -m scripts.process_job_candidates --dry-run --limit 20
python -m scripts.process_job_candidates --limit 20
```

Depois, confira o banco. Um resultado esperado é:

```text
job_candidates: mantém o histórico coletado
jobs: aumenta ou atualiza conforme candidatos processados
related_jobs: pode aumentar se o pipeline de ingestão capturar vagas relacionadas
```

## Pontos de atenção

- não usar `RelatedJob` para vagas de busca independentes;
- salvar vagas fechadas em `job_candidates`, mas marcar como `skipped` no processamento;
- não reprocessar `processed` por padrão;
- usar `--retry-failed` apenas para falhas corrigíveis;
- manter Excel como auditoria opcional, não como fonte de verdade;
- evitar `git add .` para não versionar banco, profiles, HTML/PNG e exports reais.
