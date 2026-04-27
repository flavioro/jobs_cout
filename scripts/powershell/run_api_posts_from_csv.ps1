$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "=================================================="
    Write-Host $Message
    Write-Host "=================================================="
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (!(Test-Path $Path)) {
        throw "$Label não encontrado: $Path"
    }
}

function Assert-PythonEnvironment {
    param([string]$PythonPath)

    Assert-FileExists -Path $PythonPath -Label "Python configurado"

    Write-Host "Python configurado: $PythonPath"

    & $PythonPath -c "import sys; print(sys.executable)"
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar o Python configurado: $PythonPath"
    }

    & $PythonPath -c "import sqlalchemy; print(sqlalchemy.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "O Python configurado não possui sqlalchemy instalado: $PythonPath"
    }
}

Write-Step "Importando vagas do CSV em lote"

Assert-FileExists -Path $JobsCsvImportPath -Label "CSV"
Assert-PythonEnvironment -PythonPath $PythonExe

$pythonArgs = @(
    "-m",
    "scripts.import_jobs_csv",
    "--csv-path", $JobsCsvImportPath
)

if ($JobsCsvIncludeAllStatuses) {
    $pythonArgs += "--include-all-statuses"
}
elseif ($JobsCsvStatusFilter) {
    $pythonArgs += @("--status-filter", $JobsCsvStatusFilter)
}

if ($null -ne $JobsCsvLimit) {
    $pythonArgs += @("--limit", [string]$JobsCsvLimit)
}

Push-Location $ProjectRoot
try {
    & $PythonExe @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar scripts.import_jobs_csv. ExitCode=$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
