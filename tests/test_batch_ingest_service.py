from pathlib import Path

import pytest
from types import SimpleNamespace

from src.schemas.jobs import IngestUrlResponse
from src.services.batch_ingest_service import ingest_jobs_from_csv


CSV_FIXTURE = Path(__file__).parent / "fixtures" / "csv" / "jobs_last_2_days.csv"


class MockSettings:
    csv_import_default_path = str(CSV_FIXTURE)
    csv_import_status_filter = "new"


class DummyBrowserSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch(self, url: str):
        return SimpleNamespace(url=url)


@pytest.mark.asyncio
async def test_ingest_jobs_from_csv_dry_run(monkeypatch):
    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())

    result = await ingest_jobs_from_csv(session=object(), dry_run=True, limit=2)

    assert result.status == "dry_run"
    assert result.selected_rows == 2
    assert result.processed == 0
    assert result.skipped_count == 2
    assert all(item.result_status == "dry_run" for item in result.items)


@pytest.mark.asyncio
async def test_ingest_jobs_from_csv_processes_rows(monkeypatch):
    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())
    monkeypatch.setattr("src.services.batch_ingest_service.LinkedInBrowserSession", DummyBrowserSession)

    async def fake_ingest(request, session, adapter):
        return IngestUrlResponse(status="success", source="linkedin", job_id=f"job-{request.url.split('/')[-2]}")

    monkeypatch.setattr("src.services.batch_ingest_service.ingest_linkedin_request_with_adapter", fake_ingest)

    result = await ingest_jobs_from_csv(session=object(), limit=3)

    assert result.status == "completed"
    assert result.selected_rows == 3
    assert result.processed == 3
    assert result.success_count == 3
    assert result.failed_count == 0
    assert all(item.ok for item in result.items)


@pytest.mark.asyncio
async def test_ingest_jobs_from_csv_stops_on_error(monkeypatch):
    monkeypatch.setattr("src.services.jobs_csv_import_service.get_settings", lambda: MockSettings())
    monkeypatch.setattr("src.services.batch_ingest_service.LinkedInBrowserSession", DummyBrowserSession)

    state = {"calls": 0}

    async def fake_ingest(request, session, adapter):
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("boom")
        return IngestUrlResponse(status="success", source="linkedin", job_id="job-1")

    monkeypatch.setattr("src.services.batch_ingest_service.ingest_linkedin_request_with_adapter", fake_ingest)

    result = await ingest_jobs_from_csv(session=object(), limit=3, continue_on_error=False)

    assert result.processed == 2
    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.items[-1].result_status == "exception"
