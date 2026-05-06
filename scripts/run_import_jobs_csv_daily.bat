@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%powershell\run_import_jobs_csv_daily.ps1" -ProjectRoot "%PROJECT_ROOT%" %*

exit /b %ERRORLEVEL%
