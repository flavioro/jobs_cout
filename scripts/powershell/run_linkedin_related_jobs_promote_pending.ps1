param(
    [int]$Limit = 10
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

if (-not $PSBoundParameters.ContainsKey("Limit")) {
    $Limit = $LinkedinRelatedJobsPromotePendingDefaultLimit
}

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
        [int]$TimeoutSeconds = 60
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

function Save-JsonResponse {
    param(
        [object]$Object,
        [string]$FilePath
    )

    $Object | ConvertTo-Json -Depth 20 | Set-Content -Path $FilePath -Encoding UTF8
}

if ($Limit -lt 1) {
    throw "O parâmetro -Limit deve ser maior ou igual a 1. Valor recebido: $Limit"
}

Write-Step "Aguardando API"
Wait-Api -HealthUrl "$ApiBaseUrl/health" -TimeoutSeconds 60

$headers = @{
    "x-api-key" = $ApiKey
    "Content-Type" = "application/json"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$responseFile = Join-Path $ResponsesDir "linkedin_related_jobs_promote_pending_limit_${Limit}_${timestamp}.json"
$summaryFile = Join-Path $LogsDir "linkedin_related_jobs_promote_pending_last.json"

$payload = @{
    limit = $Limit
}

$jsonBody = $payload | ConvertTo-Json -Depth 10

Write-Step "Executando POST /linkedin/related-jobs/promote-pending com limit=$Limit"

try {
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/linkedin/related-jobs/promote-pending" `
        -Method Post `
        -Headers $headers `
        -Body $jsonBody `
        -TimeoutSec 300

    Save-JsonResponse -Object $response -FilePath $responseFile
    Save-JsonResponse -Object $response -FilePath $summaryFile

    Write-Host "POST OK"
    Write-Host "requested_limit : $($response.requested_limit)"
    Write-Host "processed       : $($response.processed)"
    Write-Host "promoted        : $($response.promoted)"
    Write-Host "already_resolved: $($response.already_resolved)"
    Write-Host "failed          : $($response.failed)"
    Write-Host "skipped         : $($response.skipped)"
    Write-Host "response_file   : $responseFile"
    Write-Host "summary_file    : $summaryFile"
}
catch {
    $err = $_.Exception.Message
    Write-Host "POST FALHOU"
    Write-Host $err
    throw "Falha ao promover related jobs pendentes do LinkedIn. Veja os logs em $LogsDir"
}


exit 0
