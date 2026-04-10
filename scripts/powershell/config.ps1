$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBaseUrl = "http://$ApiHost`:$ApiPort"
$ApiKey = "changeme"

$JobUrls = @(
"https://www.linkedin.com/jobs/view/4399017778",
    "https://www.linkedin.com/jobs/view/4398643663",
    "https://www.linkedin.com/jobs/view/4398804402",
    "https://www.linkedin.com/jobs/view/4399462049",
    "https://www.linkedin.com/jobs/view/4398637755",
    "https://www.linkedin.com/jobs/view/4394459914",
    "https://www.linkedin.com/jobs/view/4392998757",
    "https://www.linkedin.com/jobs/view/4394234722",
    "https://www.linkedin.com/jobs/view/4392493585",
    "https://www.linkedin.com/jobs/view/4392018003",
    "https://www.linkedin.com/jobs/view/4321499321",
    "https://www.linkedin.com/jobs/view/4343835252"
)

$LogsDir = Join-Path $ProjectRoot "logs\powershell"
$ResponsesDir = Join-Path $LogsDir "responses"

if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

if (!(Test-Path $ResponsesDir)) {
    New-Item -ItemType Directory -Path $ResponsesDir -Force | Out-Null
}

$LinkedinRelatedJobsPromotePendingDefaultLimit = 10
$RunLinkedinRelatedJobsPromotePendingInRunAll = $true
