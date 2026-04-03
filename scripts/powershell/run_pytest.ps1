$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

$PytestLog = Join-Path $LogsDir "pytest.log"

Write-Host "Executando testes unitários..."
Write-Host "Projeto: $ProjectRoot"
Write-Host "Log: $PytestLog"

$cmdCommand = "call `"$CondaActivateBat`" && conda activate $CondaEnvName && cd /d `"$ProjectRoot`" && pytest -v"

$allOutput = & cmd.exe /c $cmdCommand 2>&1
$exitCode = $LASTEXITCODE

$allOutput | Out-File -FilePath $PytestLog -Encoding utf8

Write-Host "pytest finalizado com exit code: $exitCode"

switch ($exitCode) {
    0 { Write-Host "Testes unitários OK" }
    1 { throw "Falha em um ou mais testes unitários. Veja: $PytestLog" }
    5 { throw "Nenhum teste foi coletado. Veja: $PytestLog" }
    default { throw "pytest retornou código inesperado ($exitCode). Veja: $PytestLog" }
}