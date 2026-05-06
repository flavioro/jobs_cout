param(
    [string]$ProjectRoot = $null,
    [string]$ConfigPath = $null,
    [switch]$DryRun,
    [int]$Limit = 100,
    [switch]$NoExportXlsx,
    [switch]$RetryFailed,
    [switch]$IncludeClosed,
    [int]$MaxJobsPerUrl = 0,
    [switch]$StopOnError
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Message)

    Write-Host ""
    Write-Host "=================================================="
    Write-Host $Message
    Write-Host "=================================================="
}

function Resolve-DefaultProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Resolve-PythonExecutable {
    if (-not [string]::IsNullOrWhiteSpace($PythonExe) -and (Test-Path $PythonExe)) {
        return $PythonExe
    }

    if (-not [string]::IsNullOrWhiteSpace($CondaActivateBat) -and -not [string]::IsNullOrWhiteSpace($CondaEnvName)) {
        $CondaScriptsDir = Split-Path $CondaActivateBat -Parent
        $CondaRoot = Split-Path $CondaScriptsDir -Parent
        $CandidatePython = Join-Path $CondaRoot "envs\$CondaEnvName\python.exe"
        if (Test-Path $CandidatePython) {
            return $CandidatePython
        }
    }

    return "python"
}

function Invoke-PythonStep {
    param(
        [string]$StepName,
        [string]$Python,
        [string[]]$PythonArgs,
        [string]$WorkingDirectory
    )

    Write-Section $StepName
    Write-Host "WorkingDirectory: $WorkingDirectory"
    Write-Host "Python: $Python"
    Write-Host "Comando: $Python $($PythonArgs -join ' ')"

    Push-Location $WorkingDirectory
    try {
        & $Python @PythonArgs
        $ExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($ExitCode -ne 0) {
        throw "Etapa '$StepName' falhou com exit code $ExitCode."
    }

    Write-Host "Etapa finalizada com sucesso: $StepName"
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-DefaultProjectRoot
}

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot "config.ps1"
}

if (Test-Path $ConfigPath) {
    . $ConfigPath
}

if (-not (Test-Path $ProjectRoot)) {
    throw "ProjectRoot não encontrado: $ProjectRoot"
}

if ($Limit -le 0) {
    throw "Limit deve ser maior que zero. Valor recebido: $Limit"
}

$LogsDirResolved = $LogsDir
if ([string]::IsNullOrWhiteSpace($LogsDirResolved)) {
    $LogsDirResolved = Join-Path $ProjectRoot "logs\powershell"
}
if (!(Test-Path $LogsDirResolved)) {
    New-Item -ItemType Directory -Path $LogsDirResolved -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogsDirResolved "linkedin_candidates_pipeline_$Timestamp.log"

try {
    Start-Transcript -Path $LogPath -Append | Out-Null

    Write-Section "Iniciar pipeline diário de candidatos LinkedIn"
    Write-Host "ProjectRoot: $ProjectRoot"
    Write-Host "ConfigPath: $ConfigPath"
    Write-Host "LogPath: $LogPath"
    Write-Host "Limit: $Limit"
    Write-Host "DryRun: $DryRun"
    Write-Host "NoExportXlsx: $NoExportXlsx"
    Write-Host "RetryFailed: $RetryFailed"
    Write-Host "IncludeClosed: $IncludeClosed"
    Write-Host "MaxJobsPerUrl: $MaxJobsPerUrl"
    Write-Host "StopOnError: $StopOnError"

    $Python = Resolve-PythonExecutable
    Write-Host "Python resolvido: $Python"

    $CollectArgs = @(
        "-m",
        "scripts.collect_linkedin_search_jobs",
        "--save-candidates"
    )

    if ($NoExportXlsx) {
        $CollectArgs += "--no-export-xlsx"
    }

    if ($MaxJobsPerUrl -gt 0) {
        $CollectArgs += @("--max-jobs-per-url", $MaxJobsPerUrl.ToString())
    }

    if ($StopOnError) {
        $CollectArgs += "--stop-on-error"
    }

    if ($DryRun) {
        Write-Section "DryRun ativo"
        Write-Host "A coleta real do LinkedIn será ignorada para evitar abrir navegador/sessão."
        Write-Host "Motivo: scripts.collect_linkedin_search_jobs só aceita --dry-run em conjunto com --ingest, não com --save-candidates."
    } else {
        Invoke-PythonStep `
            -StepName "coleta LinkedIn Search para job_candidates" `
            -Python $Python `
            -PythonArgs $CollectArgs `
            -WorkingDirectory $ProjectRoot
    }

    $ProcessArgs = @(
        "-m",
        "scripts.process_job_candidates",
        "--limit",
        $Limit.ToString()
    )

    if ($DryRun) {
        $ProcessArgs += "--dry-run"
    }

    if ($RetryFailed) {
        $ProcessArgs += "--retry-failed"
    }

    if ($IncludeClosed) {
        $ProcessArgs += "--include-closed"
    }

    if ($StopOnError) {
        $ProcessArgs += "--stop-on-error"
    }

    Invoke-PythonStep `
        -StepName "processamento de job_candidates para jobs" `
        -Python $Python `
        -PythonArgs $ProcessArgs `
        -WorkingDirectory $ProjectRoot

    Write-Section "Pipeline diário de candidatos LinkedIn concluído com sucesso"
    Write-Host "Log: $LogPath"
} finally {
    try { Stop-Transcript | Out-Null } catch { }
}
