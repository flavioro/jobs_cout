$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBaseUrl = "http://$ApiHost`:$ApiPort"
$ApiKey = "changeme"

$JobUrls = @(
    "https://www.linkedin.com/jobs/view/4400590168",
    "https://www.linkedin.com/jobs/view/4399348022",
    "https://www.linkedin.com/jobs/view/4398870066",
    "https://www.linkedin.com/jobs/view/4399006795",
    "https://www.linkedin.com/jobs/view/4392998757",
    "https://www.linkedin.com/jobs/view/4400589666",
    "https://www.linkedin.com/jobs/view/4398840376"
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
