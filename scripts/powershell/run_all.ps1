$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

function Write-Step {
    param([string]$Message)

    Write-Host ""
    Write-Host "=================================================="
    Write-Host $Message
    Write-Host "=================================================="
}

function Wait-Api {
    param(
        [string]$HealthUrl,
        [int]$TimeoutSeconds = 90
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 10
            if ($null -ne $resp) {
                Write-Host "API respondeu no healthcheck."
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "API não respondeu em até $TimeoutSeconds segundos no endpoint $HealthUrl"
}

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Step $Name

    try {
        & $Action
        Write-Host "OK: $Name"
    }
    catch {
        Write-Error "FALHOU: $Name"
        Write-Error $_
        exit 1
    }
}

$startApiCmd = Join-Path $PSScriptRoot "start_api.cmd"
$runPytestPs1 = Join-Path $PSScriptRoot "run_pytest.ps1"
$runApiPostsPs1 = Join-Path $PSScriptRoot "run_api_posts.ps1"
$showDbTablesPs1 = Join-Path $PSScriptRoot "show_db_tables.ps1"

Run-Step "Validar arquivos necessários" {
    if (!(Test-Path $startApiCmd)) {
        throw "Arquivo não encontrado: $startApiCmd"
    }

    if (!(Test-Path $runPytestPs1)) {
        throw "Arquivo não encontrado: $runPytestPs1"
    }

    if (!(Test-Path $runApiPostsPs1)) {
        throw "Arquivo não encontrado: $runApiPostsPs1"
    }

    if (!(Test-Path $showDbTablesPs1)) {
        throw "Arquivo não encontrado: $showDbTablesPs1"
    }
}

Run-Step "Subir API com start_api.cmd" {
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/k", "`"$startApiCmd`"" `
        -WorkingDirectory $ProjectRoot
}

Run-Step "Aguardar API responder" {
    Wait-Api -HealthUrl "$ApiBaseUrl/health" -TimeoutSeconds 90
}

Run-Step "Executar testes unitários pytest -v" {
    & $runPytestPs1
}

Run-Step "Executar POSTs de validação" {
    & $runApiPostsPs1
}

Run-Step "Inspecionar tabelas do banco" {
    & $showDbTablesPs1
}

Write-Step "Processo finalizado"
Write-Host "Tudo executado com sucesso."
exit 0