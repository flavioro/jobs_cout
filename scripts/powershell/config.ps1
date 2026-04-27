$ProjectRoot = "D:\Python\projetos\job_scout\jobscout"
$CondaActivateBat = "D:\Python\anaconda3\Scripts\activate.bat"
$CondaEnvName = "job_scout"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBaseUrl = "http://$ApiHost`:$ApiPort"
$ApiKey = "changeme"

$JobUrls = @(
    "https://www.linkedin.com/jobs/view/4402742546"
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

$JobsCsvImportPath = "D:\Python\projetos\gmail_linkedin\linkedin_gmail_jobs_hub\exports\jobs_last_2_days.csv"
$JobsCsvStatusFilter = "new"
$JobsCsvIncludeAllStatuses = $false
$JobsCsvLimit = 100

# ============================
# NOVO: Python do ambiente
# ============================
$PythonExe = "D:\Python\anaconda3\envs\job_scout\python.exe"