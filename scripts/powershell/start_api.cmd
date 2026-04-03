@echo off
setlocal

echo ==========================================
echo Subindo API JobScout
echo ==========================================

call D:\Python\anaconda3\Scripts\activate.bat

call conda activate job_scout
if errorlevel 1 (
    echo [ERRO] Falha ao ativar ambiente job_scout
    pause
    exit /b 1
)

cd /d D:\Python\projetos\job_scout\jobscout
if errorlevel 1 (
    echo [ERRO] Falha ao entrar na pasta do projeto
    pause
    exit /b 1
)

echo Ambiente ativo:
where python
python --version

echo.
echo Iniciando uvicorn...
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

set ERR=%ERRORLEVEL%
echo.
echo Uvicorn finalizou com codigo %ERR%
pause
exit /b %ERR%