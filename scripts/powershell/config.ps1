$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBaseUrl = "http://$ApiHost`:$ApiPort"
$ApiKey = "changeme"

$JobUrls = @(
    "https://www.linkedin.com/jobs/view/4402111379",
    "https://www.linkedin.com/jobs/view/4402158096",
    "https://www.linkedin.com/jobs/view/4398637755",
    "https://www.linkedin.com/jobs/view/4397773090",
    "https://www.linkedin.com/jobs/view/4402396738"
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
