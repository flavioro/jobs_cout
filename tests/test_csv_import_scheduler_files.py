from pathlib import Path


def test_csv_import_scheduler_files_exist() -> None:
    project_root = Path(__file__).resolve().parents[1]

    assert (project_root / "scripts" / "run_import_jobs_csv_daily.bat").exists()
    assert (project_root / "scripts" / "powershell" / "run_import_jobs_csv_daily.ps1").exists()
    assert (project_root / "docs" / "csv-import-scheduler.md").exists()


def test_csv_import_scheduler_calls_existing_python_importer() -> None:
    project_root = Path(__file__).resolve().parents[1]
    ps1 = (project_root / "scripts" / "powershell" / "run_import_jobs_csv_daily.ps1").read_text(encoding="utf-8")

    assert "scripts.import_jobs_csv" in ps1
    assert "--csv-path" in ps1
    assert "--status-filter" in ps1
    assert "--include-all-statuses" in ps1


def test_csv_import_scheduler_validates_same_day_file() -> None:
    project_root = Path(__file__).resolve().parents[1]
    ps1 = (project_root / "scripts" / "powershell" / "run_import_jobs_csv_daily.ps1").read_text(encoding="utf-8")

    assert "LastWriteTime.Date" in ps1
    assert "CSV não foi atualizado hoje" in ps1
    assert "SkipSameDayValidation" in ps1


def test_csv_import_scheduler_bat_delegates_to_powershell() -> None:
    project_root = Path(__file__).resolve().parents[1]
    bat = (project_root / "scripts" / "run_import_jobs_csv_daily.bat").read_text(encoding="utf-8")

    assert "run_import_jobs_csv_daily.ps1" in bat
    assert "ExecutionPolicy Bypass" in bat
