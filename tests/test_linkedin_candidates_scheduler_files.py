from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_linkedin_candidates_scheduler_bat_exists():
    bat_path = PROJECT_ROOT / "scripts" / "run_linkedin_candidates_pipeline_daily.bat"

    assert bat_path.exists(), "BAT de agendamento do pipeline LinkedIn não foi encontrado."


def test_linkedin_candidates_scheduler_powershell_exists():
    ps1_path = (
        PROJECT_ROOT
        / "scripts"
        / "powershell"
        / "run_linkedin_candidates_pipeline_daily.ps1"
    )

    assert ps1_path.exists(), "PowerShell de agendamento do pipeline LinkedIn não foi encontrado."


def test_linkedin_candidates_scheduler_config_exists():
    config_path = PROJECT_ROOT / "scripts" / "powershell" / "config.ps1"

    assert config_path.exists(), "config.ps1 não foi encontrado em scripts/powershell."


def test_linkedin_candidates_scheduler_doc_exists():
    doc_path = PROJECT_ROOT / "docs" / "linkedin-candidates-scheduler.md"

    assert doc_path.exists(), "Documentação do agendamento LinkedIn Candidates não foi encontrada."


def test_linkedin_candidates_scheduler_bat_uses_csv_scheduler_style():
    bat_path = PROJECT_ROOT / "scripts" / "run_linkedin_candidates_pipeline_daily.bat"
    content = read(bat_path).lower()

    assert "set script_dir=%~dp0" in content
    assert "set project_root=%script_dir%.." in content
    assert "run_linkedin_candidates_pipeline_daily.ps1" in content
    assert "-projectroot" in content
    assert "powershell -noprofile -executionpolicy bypass" in content


def test_linkedin_candidates_scheduler_bat_does_not_depend_on_conda_activate():
    bat_path = PROJECT_ROOT / "scripts" / "run_linkedin_candidates_pipeline_daily.bat"
    content = read(bat_path).lower()

    assert "conda activate" not in content
    assert "call conda" not in content


def test_linkedin_candidates_scheduler_bat_sets_utf8_environment():
    bat_path = PROJECT_ROOT / "scripts" / "run_linkedin_candidates_pipeline_daily.bat"
    content = read(bat_path).lower()

    assert "chcp 65001" in content
    assert "pythonutf8=1" in content
    assert "pythonioencoding=utf-8" in content


def test_linkedin_candidates_scheduler_powershell_loads_config_and_resolves_python():
    ps1_path = (
        PROJECT_ROOT
        / "scripts"
        / "powershell"
        / "run_linkedin_candidates_pipeline_daily.ps1"
    )
    content = read(ps1_path)

    assert "config.ps1" in content
    assert "Resolve-PythonExecutable" in content
    assert "$PythonExe" in content
    assert "envs\\$CondaEnvName\\python.exe" in content
    assert "return \"python\"" in content


def test_linkedin_candidates_scheduler_powershell_uses_transcript_logs():
    ps1_path = (
        PROJECT_ROOT
        / "scripts"
        / "powershell"
        / "run_linkedin_candidates_pipeline_daily.ps1"
    )
    content = read(ps1_path)

    assert "Start-Transcript" in content
    assert "Stop-Transcript" in content
    assert "linkedin_candidates_pipeline_" in content
    assert "logs\\powershell" in content or "logs/powershell" in content


def test_linkedin_candidates_scheduler_powershell_runs_collect_and_process_commands():
    ps1_path = (
        PROJECT_ROOT
        / "scripts"
        / "powershell"
        / "run_linkedin_candidates_pipeline_daily.ps1"
    )
    content = read(ps1_path)

    assert "scripts.collect_linkedin_search_jobs" in content
    assert "--save-candidates" in content
    assert "scripts.process_job_candidates" in content
    assert "--limit" in content
    assert "$Limit = 100" in content


def test_linkedin_candidates_scheduler_powershell_supports_operational_flags():
    ps1_path = (
        PROJECT_ROOT
        / "scripts"
        / "powershell"
        / "run_linkedin_candidates_pipeline_daily.ps1"
    )
    content = read(ps1_path)

    assert "DryRun" in content
    assert "NoExportXlsx" in content
    assert "RetryFailed" in content
    assert "IncludeClosed" in content
    assert "MaxJobsPerUrl" in content
    assert "StopOnError" in content
    assert "--dry-run" in content
    assert "--no-export-xlsx" in content
    assert "--retry-failed" in content
    assert "--include-closed" in content
    assert "--max-jobs-per-url" in content
    assert "--stop-on-error" in content


def test_linkedin_candidates_scheduler_config_defines_python_exe():
    config_path = PROJECT_ROOT / "scripts" / "powershell" / "config.ps1"
    content = read(config_path)

    assert "$PythonExe" in content
    assert "envs\\job_scout\\python.exe" in content


def test_linkedin_candidates_scheduler_doc_mentions_task_scheduler_command():
    doc_path = PROJECT_ROOT / "docs" / "linkedin-candidates-scheduler.md"
    content = read(doc_path)

    assert "schtasks /create" in content
    assert "Job Scout - LinkedIn Candidates Pipeline Diario" in content
    assert "--save-candidates" in content
    assert "--limit 100" in content
    assert "Start-Transcript" in content
    assert "PythonExe" in content
