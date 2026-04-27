from pathlib import Path

import pytest

from src.core.enums import WorkplaceType
from src.services.jobs_csv_import_service import CsvImportError, read_jobs_csv


CSV_FIXTURE = Path(__file__).parent / "fixtures" / "csv" / "jobs_last_2_days.csv"


class MockSettings:
    csv_import_default_path = str(CSV_FIXTURE)
    csv_import_status_filter = "new"


def test_read_jobs_csv_uses_default_status_filter(monkeypatch):
    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())

    resolved_path, jobs, total_rows = read_jobs_csv()

    assert resolved_path == CSV_FIXTURE
    assert total_rows == 19
    assert len(jobs) == 19
    assert all(job.source_status == "new" for job in jobs)
    assert jobs[0].request.workplace_type == WorkplaceType.REMOTE
    assert jobs[0].request.is_easy_apply is True


def test_read_jobs_csv_can_limit_rows(monkeypatch):
    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())

    _, jobs, total_rows = read_jobs_csv(limit=3)

    assert total_rows == 19
    assert len(jobs) == 3


def test_read_jobs_csv_include_all_statuses(monkeypatch, tmp_path):
    csv_path = tmp_path / "mixed_jobs.csv"
    csv_path.write_text(
        "linkedin_job_url,status,title,work_model,is_easy_apply\n"
        "https://www.linkedin.com/jobs/view/1,new,Job 1,remote,True\n"
        "https://www.linkedin.com/jobs/view/2,archived,Job 2,presencial,False\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())

    _, jobs_new, _ = read_jobs_csv(str(csv_path), status_filter="new")
    _, jobs_all, _ = read_jobs_csv(str(csv_path), include_all_statuses=True)

    assert len(jobs_new) == 1
    assert len(jobs_all) == 2
    assert jobs_all[1].request.workplace_type == WorkplaceType.ONSITE


def test_read_jobs_csv_invalid_schema(monkeypatch, tmp_path):
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("status,title\nnew,Job\n", encoding="utf-8")

    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())

    with pytest.raises(CsvImportError):
        read_jobs_csv(str(csv_path))
