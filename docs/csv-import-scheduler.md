# Agendamento diário de importação CSV

Este documento descreve como agendar, no Windows Task Scheduler, a importação automática do CSV gerado pelo projeto `linkedin_gmail_jobs_hub` para o `job_scout`.

## Objetivo

Fluxo diário recomendado:

```text
linkedin_gmail_jobs_hub
→ gera exports/jobs_last_2_days.csv
→ job_scout valida se o CSV foi atualizado hoje
→ job_scout executa scripts.import_jobs_csv
→ vagas entram no pipeline de ingestão do job_scout
```

O CSV fica no outro projeto:

```powershell
D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv
```

No `job_scout`, o caminho fica configurado em:

```powershell
scripts\powershell\config.ps1
```

Variável esperada:

```powershell
$JobsCsvImportPath = "D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv"
```

## Arquivos usados

```text
scripts/import_jobs_csv.py
scripts/run_import_jobs_csv_daily.bat
scripts/powershell/run_import_jobs_csv_daily.ps1
scripts/powershell/config.ps1
```

O Python de importação já existe e é o executor principal:

```bash
python -m scripts.import_jobs_csv --csv-path "D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv" --status-filter new
```

O PowerShell é apenas um wrapper operacional para o Windows Task Scheduler.

## Validação de data do CSV

Antes de importar, o script valida:

```text
- o CSV existe;
- o CSV foi atualizado no mesmo dia da execução;
- o arquivo tem caminho válido;
- o comando Python terminou com exit code 0.
```

Se o CSV existir, mas for de outro dia, o import falha para evitar reprocessar um arquivo antigo.

## Execução manual

Da raiz do `job_scout`:

```powershell
scripts\run_import_jobs_csv_daily.bat
```

Teste sem gravar/processar de fato:

```powershell
scripts\run_import_jobs_csv_daily.bat -DryRun
```

Ignorar validação de data em ambiente de teste:

```powershell
scripts\run_import_jobs_csv_daily.bat -DryRun -SkipSameDayValidation
```

Processar todos os status do CSV:

```powershell
scripts\run_import_jobs_csv_daily.bat -IncludeAllStatuses
```

Limitar linhas processadas:

```powershell
scripts\run_import_jobs_csv_daily.bat -Limit 10
```

## Agendamento no Windows Task Scheduler

Recomendação: rodar o import alguns minutos depois da rotina que gera o CSV.

Exemplo:

```text
08:00 — linkedin_gmail_jobs_hub gera jobs_last_2_days.csv
08:30 — job_scout importa jobs_last_2_days.csv
```

### Criar via schtasks

Da raiz do `job_scout`, ajuste o horário conforme necessário:

```cmd
schtasks /create /tn "Job Scout - Import CSV Diario" /tr "D:\Python\projetos\job_scout\jobscout\scripts\run_import_jobs_csv_daily.bat" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:30
```

### Alterar o horário

```cmd
schtasks /change /tn "Job Scout - Import CSV Diario" /st 08:45
```

### Executar manualmente pelo agendador

```cmd
schtasks /run /tn "Job Scout - Import CSV Diario"
```

### Remover a tarefa

```cmd
schtasks /delete /tn "Job Scout - Import CSV Diario" /f
```

## Logs

Os logs ficam em:

```text
logs/powershell/import_jobs_csv_daily_YYYYMMDD_HHMMSS.log
```

Em caso de falha, verifique:

```text
logs/powershell/import_jobs_csv_daily_*.log
logs/powershell/pytest.log
```

## Pontos de atenção

- O projeto `linkedin_gmail_jobs_hub` precisa terminar a geração do CSV antes do import.
- O script espera o arquivo aparecer por alguns minutos antes de falhar.
- Por padrão, o import usa status `new`.
- Use `-IncludeAllStatuses` apenas quando quiser importar todas as linhas válidas do CSV.
- Mantenha o caminho `$JobsCsvImportPath` centralizado em `scripts/powershell/config.ps1`.
- Se usar outro ambiente Conda, ajuste `$CondaEnvName` e `$CondaActivateBat` no `config.ps1`.
