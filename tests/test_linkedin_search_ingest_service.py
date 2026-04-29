from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.linkedin_search_ingest_service import collect_and_ingest_search_jobs


@pytest.mark.asyncio
async def test_collect_and_ingest_search_jobs_skips_closed_and_ingests_partial(monkeypatch):
    collected = [
        {
            "linkedin_job_id": "1",
            "linkedin_job_url": "https://www.linkedin.com/jobs/view/1/",
            "title": "Python Developer",
            "company": "ACME",
            "location_raw": "Brasil",
            "extraction_status": "partial",
            "availability_status": "unknown",
            "detail_completed": False,
            "detail_url_opened": True,
        },
        {
            "linkedin_job_id": "2",
            "linkedin_job_url": "https://www.linkedin.com/jobs/view/2/",
            "title": "Chatbot Developer",
            "company": "Simbium.com",
            "location_raw": "Brasil",
            "extraction_status": "closed",
            "availability_status": "closed",
            "detail_completed": True,
        },
    ]

    async def fake_collect(*args, **kwargs):
        return collected

    class FakeBrowserSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None
        async def fetch(self, url):
            return None

    async def fake_ingest(request, session, adapter):
        assert request.url == "https://www.linkedin.com/jobs/view/1/"
        return SimpleNamespace(status="success", job_id="job-1", block_reason=None)

    monkeypatch.setattr("src.services.linkedin_search_ingest_service.collect_jobs_from_search_urls", fake_collect)
    monkeypatch.setattr("src.services.linkedin_search_ingest_service.LinkedInBrowserSession", FakeBrowserSession)
    monkeypatch.setattr("src.services.linkedin_search_ingest_service.ingest_linkedin_request_with_adapter", fake_ingest)
    monkeypatch.setattr("src.services.linkedin_search_ingest_service.export_search_cards_to_xlsx", lambda *args, **kwargs: "cards.xlsx")

    result = await collect_and_ingest_search_jobs(session=AsyncMock(), skip_closed=True, export_xlsx=True)

    assert result["processed"] == 1
    assert result["success_count"] == 1
    assert result["skipped_count"] == 1
    assert result["items"][0]["result_status"] == "success"
    assert result["items"][0]["detail_url_opened"] is True
    assert result["detail_url_opened_count"] == 1
    assert result["items"][1]["error"] == "closed_card_skipped"
    assert result["cards_xlsx_path"] == "cards.xlsx"

