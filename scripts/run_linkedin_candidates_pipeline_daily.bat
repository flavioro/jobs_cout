@echo off
setlocal

chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%powershell\run_linkedin_candidates_pipeline_daily.ps1" -ProjectRoot "%PROJECT_ROOT%" %*

exit /b %ERRORLEVEL%
