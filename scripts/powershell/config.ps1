$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBaseUrl = "http://$ApiHost`:$ApiPort"
$ApiKey = "changeme"

$JobUrls = @(
    "https://www.linkedin.com/jobs/view/4383830220",
    "https://www.linkedin.com/jobs/view/4392892148",
    "https://www.linkedin.com/jobs/view/4396673137",
    "https://www.linkedin.com/jobs/view/4396458716",
    "https://www.linkedin.com/jobs/view/4392808079",
    "https://www.linkedin.com/jobs/view/4392666873"
)

$LogsDir = Join-Path $ProjectRoot "logs\powershell"
$ResponsesDir = Join-Path $LogsDir "responses"

if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

if (!(Test-Path $ResponsesDir)) {
    New-Item -ItemType Directory -Path $ResponsesDir -Force | Out-Null
}

$LinkedinRelatedJobsPromotePendingDefaultLimit = 1
$RunLinkedinRelatedJobsPromotePendingInRunAll = $true
