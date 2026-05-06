# Job Scout

Job Scout é um pipeline para ingestão, organização e enriquecimento de vagas, com foco inicial no LinkedIn. O projeto combina scraping com Playwright, persistência em SQLite/SQLAlchemy, enriquecimento por IA e automações operacionais para transformar buscas de vagas em registros estruturados.

## Visão geral

O projeto cobre três fluxos principais:

1. **Ingestão por URL individual**  
   Recebe uma URL de vaga do LinkedIn, captura a página, extrai os dados, normaliza e grava/atualiza a tabela `jobs`.

2. **Coleta por busca do LinkedIn**  
   Abre URLs de busca do LinkedIn com sessão persistente, faz scroll incremental, captura cards de vagas, completa cards parciais abrindo a vaga individual quando necessário e gera auditoria em Excel/HTML/PNG.

3. **Fila intermediária de candidatos (`job_candidates`)**  
   Salva as vagas coletadas da busca em uma tabela intermediária. Depois, um segundo processo transforma candidatos pendentes em registros finais na tabela `jobs`, marcando cada candidato como `processed`, `skipped` ou `failed`.

Esse desenho permite separar **coleta** de **processamento**, evitando perda de dados quando a ingestão falha e permitindo auditoria/reprocessamento.

## Quick start

1. Crie e ative o ambiente virtual/conda.
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Copie `.env.example` para `.env` e ajuste as variáveis.
4. Prepare o banco local:

```bash
python migrate_db.py
```

5. Rode a API:

```bash
uvicorn src.main:app --reload
```

ou use os scripts PowerShell do projeto.

6. Rode os testes:

```bash
pytest
```

ou:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_pytest.ps1
```

## Features

- ingestão de vaga individual por URL do LinkedIn;
- normalização, deduplicação e blocklist por título;
- captura de vagas relacionadas (`related_jobs`);
- persistência em SQLite com SQLAlchemy assíncrono;
- coleta de vagas por página de busca do LinkedIn;
- scroll incremental e deduplicação por `linkedin_job_id`/URL canônica;
- detecção de vagas fechadas/expiradas;
- preenchimento de cards parciais reaproveitando o extrator do fluxo `ingest-url`;
- exportação opcional de auditoria em Excel;
- tabela intermediária `job_candidates` para staging/fila de processamento;
- processamento controlado de candidatos para a tabela final `jobs`;
- enriquecimento por Groq e provedores web;
- automação web para ChatGPT e Gemini com perfil persistente;
- logging de respostas de browser AI em JSON lines.

## Fluxo recomendado para LinkedIn Search

### 1. Login persistente no LinkedIn

```bash
python -m scripts.login_linkedin
```

Isso cria/atualiza o profile persistente configurado em `linkedin_profile_path`.

### 2. Criar ou revisar URLs de busca

Arquivo padrão:

```text
data/linkedin_search_urls.json
```

### 3. Coletar para staging table

Coleta as vagas da busca, salva/atualiza `job_candidates` e gera Excel por padrão:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates
```

Sem Excel:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates --no-export-xlsx
```

### 4. Processar staging para `jobs`

Primeiro simule:

```bash
python -m scripts.process_job_candidates --dry-run --limit 20
```

Depois processe de verdade:

```bash
python -m scripts.process_job_candidates --limit 20
```

Para reprocessar falhas:

```bash
python -m scripts.process_job_candidates --retry-failed --limit 20
```

## Tabelas principais

- `jobs`: vagas finais processadas.
- `job_candidates`: staging/fila de vagas coletadas por busca.
- `related_jobs`: vagas relacionadas capturadas durante a ingestão de uma vaga.
- `blocked_jobs`: vagas bloqueadas por regra de título/palavra-chave.

## Endpoints principais

- `POST /ingest-url`: ingere uma vaga individual.
- `POST /linkedin/search-jobs/collect-ingest`: coleta busca e ingere direto em `jobs`.
- `POST /linkedin/search-jobs/collect-candidates`: coleta busca e salva em `job_candidates`.
- `GET /job-candidates`: lista candidatos coletados.
- `POST /job-candidates/process`: processa candidatos pendentes para `jobs`.

## Documentação detalhada

- `docs/architecture.md`
- `docs/enrichment.md`
- `docs/scraping.md`
- `docs/linkedin-search.md`
- `docs/roadmap.md`

## Observação sobre Excel

O Excel deixou de ser a fonte principal do fluxo. A fonte principal agora é a tabela `job_candidates`. Ainda assim, a exportação Excel continua útil para auditoria rápida do scraper, revisão visual dos campos coletados e diagnóstico quando o LinkedIn muda o HTML.

## Observação sobre browser AI

O modo padrão é `new_chat`, mais previsível para automação. O modo `existing_chat` é suportado via URL configurável, mas traz risco maior de contaminação de contexto.


## Importação diária de CSV via Windows Task Scheduler

O `job_scout` pode importar automaticamente o CSV gerado pelo projeto `linkedin_gmail_jobs_hub`. O fluxo recomendado é agendar a geração do arquivo no projeto de origem e, alguns minutos depois, executar o import no `job_scout`.

Arquivo de origem padrão:

```text
D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv
```

Executar manualmente, validando se o CSV foi atualizado hoje:

```powershell
scripts\run_import_jobs_csv_daily.bat
```

Teste seguro sem gravar/processar:

```powershell
scripts\run_import_jobs_csv_daily.bat -DryRun
```

O wrapper chama o importador Python existente:

```bash
python -m scripts.import_jobs_csv --csv-path "D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv" --status-filter new
```

Documentação completa: [`docs/csv-import-scheduler.md`](docs/csv-import-scheduler.md).

## Pipeline LinkedIn Candidates diário via Windows Task Scheduler

Além da importação CSV, o `job_scout` também pode automatizar o fluxo de coleta e processamento de candidatos vindos do LinkedIn Search.

Fluxo operacional:

```text
LinkedIn Search
→ job_candidates
→ process_job_candidates
→ jobs
```

Execução manual das etapas Python:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates
python -m scripts.process_job_candidates --limit 100
```

Execução via wrapper diário:

```powershell
scripts\run_linkedin_candidates_pipeline_daily.bat
```

Teste seguro:

```powershell
scripts\run_linkedin_candidates_pipeline_daily.bat -DryRun
```

Execução sem gerar Excel de auditoria:

```powershell
scripts\run_linkedin_candidates_pipeline_daily.bat -NoExportXlsx
```

Agendamento sugerido:

```cmd
schtasks /create /tn "Job Scout - LinkedIn Candidates Pipeline Diario" /tr "D:\Python\projetos\job_scout\jobscout\scripts\run_linkedin_candidates_pipeline_daily.bat" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:45
```

Documentação completa: [`docs/linkedin-candidates-scheduler.md`](docs/linkedin-candidates-scheduler.md).



### Atualização do agendamento LinkedIn Candidates

O agendamento foi padronizado com o mesmo modelo do CSV: `config.ps1`, `PythonExe` absoluto e `Start-Transcript`. Consulte `docs/linkedin-candidates-scheduler.md`.
