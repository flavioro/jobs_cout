# CSV Import

## Objetivo

A feature de importação por CSV permite processar várias vagas em lote a partir de exports gerados por outro pipeline, reduzindo o custo operacional do fluxo manual de inserção uma a uma.

## Estratégia operacional

O lote é executado de forma:

- sequencial
- em uma única sessão de navegador
- com filtro configurável por status
- com suporte a `dry_run` e `limit`

Essa abordagem foi escolhida para equilibrar velocidade, estabilidade e rastreabilidade.

## Origem do arquivo

O CSV padrão pode vir de exports do projeto de coleta de e-mails/LinkedIn, por exemplo:

`D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv`

O caminho pode ser configurado no PowerShell e/ou no `.env`.

## Filtro por status

O comportamento padrão é processar apenas linhas com:

- `status = new`

Mas a feature suporta alteração por parâmetro. Também é possível configurar a execução para incluir todos os status válidos.

## Campos aproveitados

Os principais campos do CSV que podem ser mapeados para a ingestão são:

- `linkedin_job_url` → `url`
- `title` → `title`
- `location_raw` → `location_raw`
- `is_easy_apply` → `is_easy_apply`
- `seniority` → `seniority_hint`
- `work_model` → `workplace_type`
- `linkedin_job_id` → rastreabilidade/deduplicação

Campos como `email_subject`, `received_at` e `raw_metadata_json` podem ser úteis como suporte operacional e auditoria.

## Componentes envolvidos

- `src/services/jobs_csv_import_service.py`
- `src/services/batch_ingest_service.py`
- `src/api/routes_jobs.py`
- `scripts/import_jobs_csv.py`
- `scripts/powershell/run_api_posts_from_csv.ps1`

## Fluxo resumido

1. carregar o CSV
2. validar colunas mínimas
3. filtrar por status
4. aplicar deduplicação básica
5. montar payloads de ingestão
6. abrir sessão Playwright uma vez
7. ingerir uma vaga por vez
8. consolidar resultados

## Modos úteis

### Dry run
Executa leitura, filtro e seleção das linhas, sem inserir as vagas.

Útil para validar:
- caminho do arquivo
- volume selecionado
- parâmetros de filtro
- mapeamento do CSV

### Limit
Permite processar apenas parte do lote.

Útil para:
- smoke test operacional
- validação incremental
- diagnóstico de erro

## Scripts operacionais

### Python
Execução direta via módulo:

```bash
python -m scripts.import_jobs_csv --csv-path data/imports/jobs_last_2_days.csv --status-filter new --limit 5
```

### PowerShell
Execução via runner operacional do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_api_posts_from_csv.ps1
```

## Decisões de design

### Por que não paralelizar?
Porque a paralelização no navegador aumenta o risco de:

- conflito de sessão
- bloqueios do site
- erros difíceis de reproduzir
- submissões inconsistentes

### Por que reusar sessão?
Porque o maior ganho está em evitar abrir e fechar Playwright a cada item.

## Limitações atuais

- deduplicação ainda pode evoluir com checagem mais forte no banco
- extração de `company` depende da qualidade da origem
- o relatório do lote ainda pode ser expandido com agregações melhores
- o fluxo depende da estabilidade do DOM do LinkedIn
