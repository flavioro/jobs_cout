from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import JobCandidate
from src.services.job_candidate_service import (
    process_pending_job_candidates,
    upsert_job_candidates_from_cards,
)


@pytest_asyncio.fixture
async def candidate_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


def _card(job_id="1", *, status="complete", availability="unknown", title="Python Developer"):
    return {
        "linkedin_job_id": job_id,
        "linkedin_job_url": f"https://www.linkedin.com/jobs/view/{job_id}/?trackingId=abc",
        "title": title,
        "company": "ACME",
        "location_raw": "Brasil",
        "workplace_type": "remote",
        "seniority_hint": "pleno",
        "is_easy_apply": True,
        "availability_status": availability,
        "availability_reason": None,
        "extraction_status": status,
        "missing_fields": [],
        "detail_completed": True,
        "detail_url_opened": True,
        "detail_completion_source": "ingest_extractor",
        "source_search_url": "https://www.linkedin.com/jobs/search/?keywords=python",
        "card_text_raw": "ACME Python Developer",
        "detail_text": "Detalhe da vaga",
    }


@pytest.mark.asyncio
async def test_upsert_job_candidates_creates_updates_and_preserves_processed(candidate_session):
    first = await upsert_job_candidates_from_cards(candidate_session, [_card("101")])
    assert first["created_count"] == 1
    assert first["updated_count"] == 0

    candidate = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "101"))
    assert candidate is not None
    assert candidate.processing_status == "pending"
    assert candidate.canonical_source_url == "https://www.linkedin.com/jobs/view/101/"

    candidate.processing_status = "processed"
    candidate.job_id = "job-101"
    await candidate_session.commit()

    second = await upsert_job_candidates_from_cards(
        candidate_session,
        [_card("101", title="Python Developer Atualizada")],
    )
    assert second["created_count"] == 0
    assert second["updated_count"] == 1

    refreshed = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "101"))
    assert refreshed.title == "Python Developer Atualizada"
    assert refreshed.processing_status == "processed"
    assert refreshed.job_id == "job-101"


@pytest.mark.asyncio
async def test_upsert_job_candidates_marks_closed_as_skipped(candidate_session):
    result = await upsert_job_candidates_from_cards(
        candidate_session,
        [_card("202", status="closed", availability="closed", title="Chatbot Developer")],
    )
    assert result["created_count"] == 1

    candidate = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "202"))
    assert candidate.processing_status == "skipped"
    assert candidate.availability_status == "closed"


@pytest.mark.asyncio
async def test_process_pending_job_candidates_processes_open_and_skips_closed(candidate_session):
    await upsert_job_candidates_from_cards(
        candidate_session,
        [
            _card("301"),
            _card("302", status="closed", availability="closed", title="Chatbot Developer"),
        ],
    )
    closed = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "302"))
    closed.processing_status = "pending"
    await candidate_session.commit()

    class FakeBrowserSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None
        async def fetch(self, url):
            return None

    async def fake_ingest(request, session, adapter):
        assert request.url == "https://www.linkedin.com/jobs/view/301/?trackingId=abc"
        return SimpleNamespace(status="success", job_id="job-301", block_reason=None)

    result = await process_pending_job_candidates(
        session=candidate_session,
        limit=10,
        browser_session_factory=FakeBrowserSession,
        ingest_func=fake_ingest,
    )

    assert result["success_count"] == 1
    assert result["skipped_count"] == 1
    assert result["failed_count"] == 0

    open_candidate = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "301"))
    skipped_candidate = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "302"))
    assert open_candidate.processing_status == "processed"
    assert open_candidate.job_id == "job-301"
    assert skipped_candidate.processing_status == "skipped"
    assert skipped_candidate.processing_error == "closed_candidate_skipped"


@pytest.mark.asyncio
async def test_process_pending_job_candidates_dry_run_does_not_mutate(candidate_session):
    await upsert_job_candidates_from_cards(candidate_session, [_card("401")])

    class BrowserShouldNotOpen:
        def __init__(self, *args, **kwargs):
            raise AssertionError("dry_run must not open browser")

    result = await process_pending_job_candidates(
        session=candidate_session,
        dry_run=True,
        browser_session_factory=BrowserShouldNotOpen,
    )

    assert result["status"] == "dry_run"
    assert result["selected_count"] == 1
    candidate = await candidate_session.scalar(select(JobCandidate).where(JobCandidate.source_job_id == "401"))
    assert candidate.processing_status == "pending"
    assert candidate.processing_attempts == 0
