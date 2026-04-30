from fastapi.testclient import TestClient

from src.main import app


def test_linkedin_search_collect_ingest_endpoint(monkeypatch):
    async def fake_collect_and_ingest_search_jobs(
        *,
        session,
        search_items=None,
        max_jobs_per_url=None,
        continue_on_error=True,
        dry_run=False,
        skip_closed=None,
        export_xlsx=None,
        export_xlsx_path=None,
    ):
        assert dry_run is True
        assert skip_closed is True
        assert export_xlsx is True
        return {
            "status": "completed",
            "source": "linkedin_search",
            "dry_run": True,
            "total_search_urls": 1,
            "collected_count": 2,
            "complete_count": 1,
            "partial_count": 1,
            "closed_count": 0,
            "invalid_count": 0,
            "processed": 2,
            "success_count": 2,
            "failed_count": 0,
            "skipped_count": 0,
            "cards_xlsx_path": "data/exports/linkedin_search_cards.xlsx",
            "items": [
                {
                    "row_number": 1,
                    "linkedin_job_id": "123",
                    "url": "https://www.linkedin.com/jobs/view/123/",
                    "title": "Python Developer",
                    "company": "ACME",
                    "extraction_status": "complete",
                    "availability_status": "unknown",
                    "detail_completed": False,
                    "ok": True,
                    "skipped": False,
                    "job_id": "job-1",
                    "result_status": "success",
                    "error": None,
                }
            ],
        }

    monkeypatch.setattr(
        "src.api.routes_jobs.collect_and_ingest_search_jobs",
        fake_collect_and_ingest_search_jobs,
    )

    client = TestClient(app)
    response = client.post(
        "/linkedin/search-jobs/collect-ingest",
        headers={"X-API-Key": "changeme"},
        json={
            "search_urls": [
                {"name": "python", "url": "https://www.linkedin.com/jobs/search/?keywords=python", "enabled": True}
            ],
            "max_jobs_per_url": 5,
            "continue_on_error": True,
            "dry_run": True,
            "skip_closed": True,
            "export_xlsx": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["source"] == "linkedin_search"
    assert payload["dry_run"] is True
    assert payload["processed"] == 2
    assert payload["complete_count"] == 1
    assert payload["cards_xlsx_path"].endswith("linkedin_search_cards.xlsx")
    assert payload["items"][0]["job_id"] == "job-1"


def test_linkedin_search_collect_candidates_endpoint(monkeypatch):
    async def fake_collect_candidates(*, session, search_items=None, max_jobs_per_url=None, export_xlsx=None, export_xlsx_path=None):
        assert max_jobs_per_url == 5
        assert export_xlsx is False
        return {
            "status": "completed",
            "source": "linkedin_search",
            "collected_count": 2,
            "complete_count": 1,
            "partial_count": 0,
            "closed_count": 1,
            "invalid_count": 0,
            "created_count": 2,
            "updated_count": 0,
            "skipped_count": 0,
            "items": [],
        }

    monkeypatch.setattr("src.api.routes_jobs.collect_linkedin_search_jobs_to_candidates", fake_collect_candidates)

    client = TestClient(app)
    response = client.post(
        "/linkedin/search-jobs/collect-candidates",
        headers={"X-API-Key": "changeme"},
        json={
            "search_urls": [
                {"name": "python", "url": "https://www.linkedin.com/jobs/search/?keywords=python", "enabled": True}
            ],
            "max_jobs_per_url": 5,
            "export_xlsx": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 2
    assert payload["closed_count"] == 1


def test_process_job_candidates_endpoint(monkeypatch):
    async def fake_process_candidates(*, session, source, limit, dry_run, retry_failed, skip_closed, continue_on_error):
        assert source == "linkedin"
        assert limit == 10
        assert dry_run is True
        return {
            "status": "dry_run",
            "source": "job_candidates",
            "dry_run": True,
            "selected_count": 3,
            "processed": 0,
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 3,
            "items": [],
        }

    monkeypatch.setattr("src.api.routes_jobs.process_pending_job_candidates", fake_process_candidates)

    client = TestClient(app)
    response = client.post(
        "/job-candidates/process",
        headers={"X-API-Key": "changeme"},
        json={"source": "linkedin", "limit": 10, "dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["selected_count"] == 3
