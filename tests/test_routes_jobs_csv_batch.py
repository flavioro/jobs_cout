from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app


def test_ingest_csv_endpoint(monkeypatch):
    async def fake_ingest_jobs_from_csv(**kwargs):
        from src.schemas.jobs import CsvBatchIngestResponse, CsvBatchIngestItem

        assert kwargs["status_filter"] == "new"
        assert kwargs["limit"] == 2
        return CsvBatchIngestResponse(
            status="completed",
            csv_path="tests/fixtures/csv/jobs_last_2_days.csv",
            dry_run=False,
            requested_status_filter="new",
            effective_status_filter="new",
            total_rows=19,
            selected_rows=2,
            processed=2,
            success_count=2,
            failed_count=0,
            skipped_count=0,
            items=[
                CsvBatchIngestItem(
                    row_number=2,
                    source_status="new",
                    linkedin_job_id="123",
                    url="https://www.linkedin.com/jobs/view/123/",
                    title="Job 123",
                    selected=True,
                    ok=True,
                    skipped=False,
                    job_id="job-123",
                    result_status="success",
                )
            ],
        )

    monkeypatch.setattr("src.api.routes_jobs.ingest_jobs_from_csv", fake_ingest_jobs_from_csv)
    client = TestClient(app)
    response = client.post(
        "/ingest-csv",
        headers={"X-API-Key": "changeme"},
        json={
            "csv_path": "tests/fixtures/csv/jobs_last_2_days.csv",
            "status_filter": "new",
            "limit": 2,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["selected_rows"] == 2
    assert payload["items"][0]["job_id"] == "job-123"
