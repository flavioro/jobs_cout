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

function Assert-NotNull {
    param(
        [object]$Value,
        [string]$Message
    )
    if ($null -eq $Value) {
        throw $Message
    }
}

function Save-JsonResponse {
    param(
        [object]$Object,
        [string]$FilePath
    )
    $Object | ConvertTo-Json -Depth 20 | Set-Content -Path $FilePath -Encoding UTF8
}

Write-Step "Aguardando API"
Wait-Api -HealthUrl "$ApiBaseUrl/health" -TimeoutSeconds 60

$headers = @{
    "x-api-key" = $ApiKey
    "Content-Type" = "application/json"
}

$results = @()
$index = 0

foreach ($jobUrl in $JobUrls) {
    $index++
    Write-Step "Executando POST $index de $($JobUrls.Count): $jobUrl"

    $payload = @{
        url = $jobUrl
    }

    $jsonBody = $payload | ConvertTo-Json -Depth 10
    $safeName = $jobUrl.Split('/')[-1]
    $responseFile = Join-Path $ResponsesDir "post_${index}_${safeName}.json"

    try {
        $response = Invoke-RestMethod `
            -Uri "$ApiBaseUrl/ingest-url" `
            -Method Post `
            -Headers $headers `
            -Body $jsonBody `
            -TimeoutSec 180

        Save-JsonResponse -Object $response -FilePath $responseFile

        Assert-NotNull $response "Resposta nula para $jobUrl"

        $statusValue = $null
        $jobIdValue = $null
        $availabilityStatus = $null
        $applyUrl = $null
        $isEasyApply = $null
        $workplaceType = $null

        if ($response.PSObject.Properties.Name -contains "status") {
            $statusValue = $response.status
        }

        if ($response.PSObject.Properties.Name -contains "job_id") {
            $jobIdValue = $response.job_id
        }

        if (($response.PSObject.Properties.Name -contains "job") -and $null -ne $response.job) {
            if ($response.job.PSObject.Properties.Name -contains "availability_status") {
                $availabilityStatus = $response.job.availability_status
            }
            if ($response.job.PSObject.Properties.Name -contains "apply_url") {
                $applyUrl = $response.job.apply_url
            }
            if ($response.job.PSObject.Properties.Name -contains "is_easy_apply") {
                $isEasyApply = $response.job.is_easy_apply
            }
            if ($response.job.PSObject.Properties.Name -contains "workplace_type") {
                $workplaceType = $response.job.workplace_type
            }
        }

        $result = [PSCustomObject]@{
            index               = $index
            url                 = $jobUrl
            ok                  = $true
            response_file       = $responseFile
            status              = $statusValue
            job_id              = $jobIdValue
            availability_status = $availabilityStatus
            apply_url           = $applyUrl
            is_easy_apply       = $isEasyApply
            workplace_type      = $workplaceType
            error               = $null
        }

        $results += $result

        Write-Host "POST OK"
        Write-Host "status: $statusValue"
        Write-Host "job_id: $jobIdValue"
        Write-Host "availability_status: $availabilityStatus"
        Write-Host "is_easy_apply: $isEasyApply"
        Write-Host "workplace_type: $workplaceType"
        Write-Host "response_file: $responseFile"
    }
    catch {
        $err = $_.Exception.Message

        $result = [PSCustomObject]@{
            index               = $index
            url                 = $jobUrl
            ok                  = $false
            response_file       = $responseFile
            status              = $null
            job_id              = $null
            availability_status = $null
            apply_url           = $null
            is_easy_apply       = $null
            workplace_type      = $null
            error               = $err
        }

        $results += $result

        Write-Host "POST FALHOU"
        Write-Host $err
    }
}

Write-Step "Resumo dos POSTs"
$results | Format-Table -AutoSize

$summaryFile = Join-Path $LogsDir "api_posts_summary.json"
$results | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryFile -Encoding UTF8

Write-Host "Resumo salvo em: $summaryFile"

$failed = $results | Where-Object { $_.ok -eq $false }
if ($failed.Count -gt 0) {
    throw "Um ou mais POSTs falharam. Veja o resumo em $summaryFile"
}

Write-Host "Todos os POSTs executaram com sucesso."