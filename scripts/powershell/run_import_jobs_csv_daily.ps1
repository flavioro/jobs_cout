param(
    [string]$ProjectRoot = $null,
    [string]$ConfigPath = $null,
    [string]$CsvPath = $null,
    [string]$StatusFilter = $null,
    [switch]$IncludeAllStatuses,
    [int]$Limit = 0,
    [switch]$DryRun,
    [switch]$StopOnError,
    [int]$WaitTimeoutMinutes = 30,
    [int]$PollSeconds = 30,
    [switch]$SkipSameDayValidation
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

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-DefaultProjectRoot
}

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot "config.ps1"
}

if (Test-Path $ConfigPath) {
    . $ConfigPath
}

if ([string]::IsNullOrWhiteSpace($CsvPath)) {
    if (-not [string]::IsNullOrWhiteSpace($JobsCsvImportPath)) {
        $CsvPath = $JobsCsvImportPath
    }
}

if ([string]::IsNullOrWhiteSpace($StatusFilter)) {
    if (-not [string]::IsNullOrWhiteSpace($JobsCsvStatusFilter)) {
        $StatusFilter = $JobsCsvStatusFilter
    } else {
        $StatusFilter = "new"
    }
}

if (-not $IncludeAllStatuses -and $JobsCsvIncludeAllStatuses -eq $true) {
    $IncludeAllStatuses = $true
}

if ($Limit -le 0 -and $JobsCsvLimit -gt 0) {
    $Limit = [int]$JobsCsvLimit
}

if ([string]::IsNullOrWhiteSpace($CsvPath)) {
    throw "CsvPath não informado. Defina `$JobsCsvImportPath em scripts\powershell\config.ps1 ou passe -CsvPath."
}

if (-not (Test-Path $ProjectRoot)) {
    throw "ProjectRoot não encontrado: $ProjectRoot"
}

$LogsDirResolved = $LogsDir
if ([string]::IsNullOrWhiteSpace($LogsDirResolved)) {
    $LogsDirResolved = Join-Path $ProjectRoot "logs\powershell"
}
if (!(Test-Path $LogsDirResolved)) {
    New-Item -ItemType Directory -Path $LogsDirResolved -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogsDirResolved "import_jobs_csv_daily_$Timestamp.log"

function Wait-ForCsvFile {
    param(
        [string]$Path,
        [int]$TimeoutMinutes,
        [int]$IntervalSeconds
    )

    $Deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ((Get-Date) -le $Deadline) {
        if (Test-Path $Path) {
            return (Get-Item $Path)
        }
        Write-Host "CSV ainda não encontrado. Aguardando $IntervalSeconds segundo(s): $Path"
        Start-Sleep -Seconds $IntervalSeconds
    }

    throw "CSV não encontrado dentro de $TimeoutMinutes minuto(s): $Path"
}

function Assert-CsvUpdatedToday {
    param([System.IO.FileInfo]$FileInfo)

    $CsvLastWriteDate = $FileInfo.LastWriteTime.Date
    $Today = (Get-Date).Date

    if ($CsvLastWriteDate -ne $Today) {
        throw "CSV não foi atualizado hoje. Arquivo: $($FileInfo.FullName). Última atualização: $($FileInfo.LastWriteTime). Hoje: $(Get-Date)."
    }
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

try {
    Start-Transcript -Path $LogPath -Append | Out-Null

    Write-Section "Validar CSV de importação"
    Write-Host "ProjectRoot: $ProjectRoot"
    Write-Host "CsvPath: $CsvPath"
    Write-Host "LogPath: $LogPath"

    $CsvFile = Wait-ForCsvFile -Path $CsvPath -TimeoutMinutes $WaitTimeoutMinutes -IntervalSeconds $PollSeconds
    Write-Host "CSV encontrado: $($CsvFile.FullName)"
    Write-Host "Última atualização: $($CsvFile.LastWriteTime)"
    Write-Host "Tamanho: $($CsvFile.Length) bytes"

    if (-not $SkipSameDayValidation) {
        Assert-CsvUpdatedToday -FileInfo $CsvFile
        Write-Host "OK: CSV atualizado hoje."
    } else {
        Write-Host "Aviso: validação de data do CSV ignorada por -SkipSameDayValidation."
    }

    Write-Section "Executar importação no job_scout"
    $Python = Resolve-PythonExecutable
    Write-Host "Python: $Python"

    $PythonArgs = @("-m", "scripts.import_jobs_csv", "--csv-path", $CsvFile.FullName)

    if ($IncludeAllStatuses) {
        $PythonArgs += "--include-all-statuses"
    } elseif (-not [string]::IsNullOrWhiteSpace($StatusFilter)) {
        $PythonArgs += @("--status-filter", $StatusFilter)
    }

    if ($Limit -gt 0) {
        $PythonArgs += @("--limit", $Limit.ToString())
    }

    if ($DryRun) {
        $PythonArgs += "--dry-run"
    }

    if ($StopOnError) {
        $PythonArgs += "--stop-on-error"
    }

    Push-Location $ProjectRoot
    try {
        Write-Host "Comando: $Python $($PythonArgs -join ' ')"
        & $Python @PythonArgs
        $ExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($ExitCode -ne 0) {
        throw "Importação finalizada com exit code $ExitCode. Veja o log: $LogPath"
    }

    Write-Section "Importação concluída com sucesso"
    Write-Host "Log: $LogPath"
} finally {
    try { Stop-Transcript | Out-Null } catch { }
}
