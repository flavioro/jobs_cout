# Agendamento diário — LinkedIn Candidates Pipeline

Este documento descreve a rotina diária que coleta vagas do LinkedIn Search, salva na tabela intermediária `job_candidates` e processa os candidatos pendentes para a tabela principal `jobs`.

## Objetivo

Executar em sequência:

```bash
python -m scripts.collect_linkedin_search_jobs --save-candidates
python -m scripts.process_job_candidates --limit 100
```

A rotina foi padronizada para seguir o mesmo modelo do agendamento de importação CSV, que já funciona no Windows Task Scheduler.

## Arquivos envolvidos

```text
scripts/run_linkedin_candidates_pipeline_daily.bat
scripts/powershell/run_linkedin_candidates_pipeline_daily.ps1
scripts/powershell/config.ps1
docs/linkedin-candidates-scheduler.md
tests/test_linkedin_candidates_scheduler_files.py
```

## Padrão técnico adotado

O `.bat` não depende mais de `conda activate`. Ele chama o PowerShell e o PowerShell resolve o Python pelo `config.ps1`.

O `config.ps1` deve conter:

```powershell
$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"
$PythonExe = "D:\Python\anaconda3\envs\job_scout\python.exe"
$LogsDir = Join-Path $ProjectRoot "logs\powershell"
```

Este padrão é mais robusto no Agendador porque usa diretamente:

```text
D:\Python\anaconda3\envs\job_scout\python.exe
```

em vez de depender de `python` disponível no `PATH` ou de `conda activate` dentro do contexto do Windows Task Scheduler.

## Execução manual

Na raiz do projeto:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat
```

Com limite customizado:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -Limit 50
```

Sem exportar Excel de auditoria:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -NoExportXlsx
```

Reprocessando falhas:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -RetryFailed -Limit 100
```

Incluindo vagas fechadas no processamento:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -IncludeClosed -Limit 100
```

Limitando a coleta por URL de busca:

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -MaxJobsPerUrl 20
```

## DryRun

```cmd
scripts\run_linkedin_candidates_pipeline_daily.bat -DryRun
```

No `-DryRun`, a coleta real do LinkedIn é ignorada para evitar abrir navegador/sessão. O processamento roda em simulação:

```bash
python -m scripts.process_job_candidates --limit 100 --dry-run
```

Isso acontece porque `scripts.collect_linkedin_search_jobs` só aceita `--dry-run` junto com `--ingest`, e não junto com `--save-candidates`.

## Logs

Os logs são gravados em:

```text
logs\powershell\linkedin_candidates_pipeline_YYYYMMDD_HHMMSS.log
```

O PowerShell usa `Start-Transcript`, seguindo o padrão do agendamento CSV, para capturar melhor stdout, stderr, comandos e exceções no Windows.

## Criar a tarefa no Agendador

Crie dentro da pasta `Jobs`:

```cmd
schtasks /create /tn "\Jobs\Job Scout - LinkedIn Candidates Pipeline Diario" /tr "D:\Python\projetos\job_scout\jobscout\scripts\run_linkedin_candidates_pipeline_daily.bat" /sc daily /st 09:15
```

Depois, no Agendador de Tarefas, edite a ação e confirme:

**Programa/script**

```text
D:\Python\projetos\job_scout\jobscout\scripts\run_linkedin_candidates_pipeline_daily.bat
```

**Adicionar argumentos**

```text
```

vazio.

**Iniciar em**

```text
D:\Python\projetos\job_scout\jobscout
```

Na aba **Geral**, para fluxos com Playwright/Chrome/LinkedIn, prefira:

```text
Executar somente quando o usuário estiver conectado
```

## Executar pelo Agendador

```cmd
schtasks /run /tn "\Jobs\Job Scout - LinkedIn Candidates Pipeline Diario"
```

Verificar resultado:

```cmd
schtasks /query /tn "\Jobs\Job Scout - LinkedIn Candidates Pipeline Diario" /fo LIST /v
```

Resultado esperado:

```text
Último resultado: 0
```

## Ordem recomendada das rotinas diárias

```text
08:00  linkedin_gmail_jobs_hub gera CSV jobs_last_2_days.csv
08:30  job_scout importa CSV externo
09:15  job_scout coleta LinkedIn Search para job_candidates e processa candidatos
```

## Testes

Teste focado:

```cmd
pytest -q tests/test_linkedin_candidates_scheduler_files.py
```

Suite padrão do projeto:

```cmd
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_pytest.ps1
```
