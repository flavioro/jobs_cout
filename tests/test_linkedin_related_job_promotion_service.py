from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.enums import AvailabilityStatus, JobSource, JobStatus
from src.db.base import Base
from src.db.models import Job, RelatedJob
from src.schemas.jobs import ConfirmationPayload, IngestUrlResponse
from src.services.linkedin_related_job_promotion_service import promote_pending_linkedin_related_jobs


async def _create_schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_promote_pending_linkedin_related_jobs_marks_existing_job_as_promoted(tmp_path):
    db_path = tmp_path / "promotion_existing.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    await _create_schema(engine)

    parent_job_id = str(uuid.uuid4())
    resolved_job_id = str(uuid.uuid4())

    async with SessionLocal() as session:
        session.add_all([
            Job(
                id=parent_job_id,
                source="linkedin",
                external_id="999",
                url="https://www.linkedin.com/jobs/view/999/",
                canonical_url="https://www.linkedin.com/jobs/view/999/",
                title="Parent",
                company="Acme",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-parent",
                collected_at=datetime.now(timezone.utc),
            ),
            Job(
                id=resolved_job_id,
                source="linkedin",
                external_id="100",
                url="https://www.linkedin.com/jobs/view/100/",
                canonical_url="https://www.linkedin.com/jobs/view/100/",
                title="Resolved",
                company="Company X",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-resolved",
                collected_at=datetime.now(timezone.utc),
            ),
            RelatedJob(
                parent_job_id=parent_job_id,
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/view/100/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related",
                company="Company X",
                promotion_status="pending",
            ),
        ])
        await session.commit()

        response = await promote_pending_linkedin_related_jobs(session, limit=10)
        item = (await session.execute(select(RelatedJob))).scalar_one()

        assert response.processed == 1
        assert response.promoted == 0
        assert response.already_resolved == 1
        assert item.is_promoted_to_job is True
        assert item.promotion_status == "promoted"
        assert item.resolved_job_id == resolved_job_id
        assert item.last_promoted_at is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_promote_pending_linkedin_related_jobs_ingests_and_links_job(tmp_path, monkeypatch):
    db_path = tmp_path / "promotion_ingest.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    await _create_schema(engine)

    parent_job_id = str(uuid.uuid4())
    promoted_job_id = str(uuid.uuid4())

    async def fake_ingest_linkedin_request(request, session):
        session.add(
            Job(
                id=promoted_job_id,
                source="linkedin",
                external_id="101",
                url=request.url,
                canonical_url=request.url,
                title="Promoted",
                company="Company Y",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v2.0",
                status="success",
                fingerprint="fp-promoted",
                collected_at=datetime.now(timezone.utc),
            )
        )
        await session.flush()
        return IngestUrlResponse(
            status="success",
            source="linkedin",
            job_id=promoted_job_id,
            parser_version="linkedin_v2.0",
            confirmation=ConfirmationPayload(
                title="match",
                company="match",
                location_raw="missing",
                is_easy_apply="missing",
                seniority_hint="missing",
                workplace_type="missing",
            ),
            job={"related_jobs_count": 0},
        )

    monkeypatch.setattr(
        "src.services.linkedin_related_job_promotion_service.ingest_linkedin_request",
        fake_ingest_linkedin_request,
    )

    async with SessionLocal() as session:
        session.add_all([
            Job(
                id=parent_job_id,
                source="linkedin",
                external_id="999",
                url="https://www.linkedin.com/jobs/view/999/",
                canonical_url="https://www.linkedin.com/jobs/view/999/",
                title="Parent",
                company="Acme",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-parent",
                collected_at=datetime.now(timezone.utc),
            ),
            RelatedJob(
                parent_job_id=parent_job_id,
                related_external_id="101",
                related_url="https://www.linkedin.com/jobs/view/101/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                title="Related Pending",
                company="Company Y",
                promotion_status="pending",
            ),
        ])
        await session.commit()

        response = await promote_pending_linkedin_related_jobs(session, limit=10)
        item = (await session.execute(select(RelatedJob))).scalar_one()

        assert response.processed == 1
        assert response.promoted == 1
        assert response.failed == 0
        assert item.is_promoted_to_job is True
        assert item.promotion_status == "promoted"
        assert item.resolved_job_id == promoted_job_id
        assert item.promotion_attempts == 1
        assert item.last_promotion_error is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_promote_pending_linkedin_related_jobs_marks_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "promotion_failed.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    await _create_schema(engine)

    parent_job_id = str(uuid.uuid4())

    async def fake_ingest_linkedin_request(request, session):
        raise RuntimeError("playwright timeout")

    monkeypatch.setattr(
        "src.services.linkedin_related_job_promotion_service.ingest_linkedin_request",
        fake_ingest_linkedin_request,
    )

    async with SessionLocal() as session:
        session.add_all([
            Job(
                id=parent_job_id,
                source="linkedin",
                external_id="999",
                url="https://www.linkedin.com/jobs/view/999/",
                canonical_url="https://www.linkedin.com/jobs/view/999/",
                title="Parent",
                company="Acme",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-parent",
                collected_at=datetime.now(timezone.utc),
            ),
            RelatedJob(
                parent_job_id=parent_job_id,
                related_external_id="102",
                related_url="https://www.linkedin.com/jobs/view/102/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/102/",
                title="Related Pending",
                company="Company Z",
                promotion_status="pending",
            ),
        ])
        await session.commit()

        response = await promote_pending_linkedin_related_jobs(session, limit=10)
        item = (await session.execute(select(RelatedJob))).scalar_one()

        assert response.processed == 1
        assert response.promoted == 0
        assert response.failed == 1
        assert item.promotion_status == "failed"
        assert item.is_promoted_to_job is False
        assert item.promotion_attempts == 1
        assert item.last_promotion_error == "playwright timeout"

    await engine.dispose()


@pytest.mark.asyncio
async def test_promote_pending_linkedin_related_jobs_handles_blocked_status(monkeypatch, tmp_path):
    """Teste que garante que o RelatedJob é marcado como 'blocked' quando a ingestão for barrada pelo título."""
    db_path = tmp_path / "promotion_blocked.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    await _create_schema(engine)

    async def mock_ingest_request(request, session):
        return IngestUrlResponse(
            status="blocked",
            source="linkedin",
            job_id=None,
            block_reason="Palavra bloqueada: 'marketing'"
        )

    monkeypatch.setattr(
        "src.services.linkedin_related_job_promotion_service.ingest_linkedin_request",
        mock_ingest_request,
    )

    parent_job_id = str(uuid.uuid4())

    async with SessionLocal() as session:
        session.add_all([
            Job(
                id=parent_job_id,
                source="linkedin",
                external_id="999",
                url="https://www.linkedin.com/jobs/view/999/",
                canonical_url="https://www.linkedin.com/jobs/view/999/",
                title="Parent",
                company="Acme",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-parent",
                collected_at=datetime.now(timezone.utc),
            ),
            RelatedJob(
                parent_job_id=parent_job_id,
                related_external_id="101",
                related_url="https://www.linkedin.com/jobs/view/101/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                title="Analista de Marketing",
                company="Company M",
                promotion_status="pending",
            ),
        ])
        await session.commit()

        response = await promote_pending_linkedin_related_jobs(session, limit=10)
        item = (await session.execute(select(RelatedJob))).scalar_one()

        assert response.processed == 1
        assert response.promoted == 0
        assert response.failed == 1 
        assert item.promotion_status == "blocked"
        assert item.is_promoted_to_job is False
        assert item.promotion_attempts == 1
        assert item.last_promotion_error == "Palavra bloqueada: 'marketing'"