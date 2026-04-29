import zipfile
from pathlib import Path

import pytest

from src.services.linkedin_search_collection_service import collect_jobs_from_search_urls, export_search_cards_to_xlsx, summarize_cards


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch_search_page(self, url: str) -> str:
        return Path("tests/fixtures/linkedin_search/linkedin_python_search.html").read_text(encoding="utf-8")


class _FakeBrowserCardsSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def fetch_search_cards(self, url: str):
        return [
            {
                "linkedin_job_id": "1",
                "linkedin_job_url": "https://www.linkedin.com/jobs/view/1/",
                "title": "Python Developer",
                "company": "ACME",
                "location_raw": "Brasil (Remoto)",
                "card_text_raw": "Python Developer ACME Brasil (Remoto)",
                "detail_completed": False,
                "detail_url_opened": False,
            },
            {
                "linkedin_job_id": "2",
                "linkedin_job_url": "https://www.linkedin.com/jobs/view/2/",
                "title": "Chatbot Developer",
                "company": "Simbium.com",
                "location_raw": "Brasil",
                "card_text_raw": "Chatbot Developer Simbium.com Brasil Expirado",
                "availability_status": "closed",
                "availability_reason": "expired_or_no_longer_accepting_applications",
                "detail_completed": False,
                "detail_url_opened": False,
            },
            {
                "linkedin_job_id": "3",
                "linkedin_job_url": "https://www.linkedin.com/jobs/view/3/",
                "title": "Backend Python",
                "company": "Example",
                "location_raw": "São Paulo",
                "card_text_raw": "link parcial",
                "detail_text": "Backend Python Example São Paulo",
                "detail_completed": True,
                "detail_url_opened": True,
            },
        ]

    async def fetch_search_page(self, url: str) -> str:
        return ""


@pytest.mark.asyncio
async def test_collect_jobs_from_search_urls_deduplicates_across_urls():
    search_items = [
        {"name": "python-1", "url": "https://example.com/1", "enabled": True},
        {"name": "python-2", "url": "https://example.com/2", "enabled": True},
    ]

    items = await collect_jobs_from_search_urls(
        search_items=search_items,
        max_jobs_per_url=10,
        session_factory=_FakeSession,
        export_xlsx=False,
    )

    assert len(items) == 10
    assert items[0]["linkedin_job_id"] == "4243924693"
    assert items[0]["source_search_url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_collect_jobs_from_browser_cards_and_exports_xlsx(tmp_path):
    output = tmp_path / "cards.xlsx"
    items = await collect_jobs_from_search_urls(
        search_items=[{"name": "python", "url": "https://example.com/search", "enabled": True}],
        session_factory=_FakeBrowserCardsSession,
        export_xlsx=True,
        export_xlsx_path=str(output),
    )

    assert len(items) == 3
    assert items[0]["extraction_status"] == "complete"
    assert items[1]["extraction_status"] == "closed"
    assert items[2]["extraction_status"] == "complete"
    assert items[2]["detail_completed"] is True
    assert items[2]["detail_url_opened"] is True
    assert output.exists()
    with zipfile.ZipFile(output) as zf:
        assert "xl/worksheets/sheet1.xml" in zf.namelist()
        sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "Python Developer" in sheet_xml
        assert "Simbium.com" in sheet_xml
        assert "Backend Python" in sheet_xml


def test_summarize_cards_counts_statuses_and_detail_completion():
    summary = summarize_cards([
        {"extraction_status": "complete", "availability_status": "unknown", "detail_completed": False, "detail_url_opened": False},
        {"extraction_status": "partial", "availability_status": "unknown", "detail_completed": False, "detail_url_opened": True},
        {"extraction_status": "closed", "availability_status": "closed", "detail_completed": False, "detail_url_opened": False},
        {"extraction_status": "complete", "availability_status": "unknown", "detail_completed": True, "detail_url_opened": True},
    ])

    assert summary["total"] == 4
    assert summary["complete"] == 2
    assert summary["partial"] == 1
    assert summary["closed"] == 1
    assert summary["detail_completed"] == 1
    assert summary["detail_url_opened"] == 2
