from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Job, RelatedJob
from src.services.persistence_service import list_related_jobs, upsert_job
from src.schemas.jobs import JobRecordSchema, RelatedJobSchema
from src.core.enums import AvailabilityStatus, JobSource, JobStatus


@pytest.mark.asyncio
async def test_list_related_jobs_returns_paginated_items(tmp_path):
    db_path = tmp_path / "related_jobs_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    job_id = str(uuid.uuid4())
    other_job_id = str(uuid.uuid4())

    async with SessionLocal() as session:
        session.add_all([
            Job(
                id=job_id,
                source="linkedin",
                url="https://www.linkedin.com/jobs/view/1",
                canonical_url="https://www.linkedin.com/jobs/view/1/",
                title="Parent Job",
                company="Acme",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp1",
                collected_at=datetime.now(timezone.utc),
            ),
            Job(
                id=other_job_id,
                source="linkedin",
                url="https://www.linkedin.com/jobs/view/2",
                canonical_url="https://www.linkedin.com/jobs/view/2/",
                title="Other Parent",
                company="Beta",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp2",
                collected_at=datetime.now(timezone.utc),
            ),
        ])
        await session.flush()
        session.add_all([
            RelatedJob(
                parent_job_id=job_id,
                related_url="https://www.linkedin.com/jobs/view/100/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related A",
                company="Company X",
                workplace_type="remote",
                is_easy_apply=True,
            ),
            RelatedJob(
                parent_job_id=job_id,
                related_url="https://www.linkedin.com/jobs/view/101/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                title="Related B",
                company="Company Y",
                workplace_type="hybrid",
                is_easy_apply=False,
            ),
            RelatedJob(
                parent_job_id=other_job_id,
                related_url="https://www.linkedin.com/jobs/view/102/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/102/",
                title="Related C",
                company="Company X",
                workplace_type="remote",
                is_easy_apply=False,
            ),
        ])
        await session.commit()

        result = await list_related_jobs(session, limit=10, offset=0)
        assert result.total == 3
        assert len(result.items) == 3

        filtered = await list_related_jobs(session, parent_job_id=job_id, limit=10, offset=0)
        assert filtered.total == 2
        assert all(item.parent_job_id == job_id for item in filtered.items)

        filtered_company = await list_related_jobs(session, company="Company X", limit=10, offset=0)
        assert filtered_company.total == 2

        filtered_remote = await list_related_jobs(session, workplace_type="remote", limit=10, offset=0)
        assert filtered_remote.total == 2

        filtered_easy_apply = await list_related_jobs(session, is_easy_apply=True, limit=10, offset=0)
        assert filtered_easy_apply.total == 1
        assert filtered_easy_apply.items[0].title == "Related A"

    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_job_deduplicates_related_jobs_by_canonical_url(tmp_path):
    db_path = tmp_path / "related_jobs_upsert.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    record = JobRecordSchema(
        source=JobSource.LINKEDIN,
        url="https://www.linkedin.com/jobs/view/999/",
        canonical_url="https://www.linkedin.com/jobs/view/999/",
        title="Parent Job",
        company="Acme",
        parser_used="linkedin_css_bs4",
        parser_version="linkedin_v1.2",
        status=JobStatus.SUCCESS,
        availability_status=AvailabilityStatus.OPEN,
        collected_at=datetime.now(timezone.utc),
        fingerprint="fp-parent",
        related_jobs=[
            RelatedJobSchema(
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/collections/similar-jobs/?currentJobId=100",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related A",
                company="Company X",
            ),
            RelatedJobSchema(
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/collections/similar-jobs/?currentJobId=100&trackingId=abc",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related A duplicate",
                company="Company X",
            ),
        ],
    )

    async with SessionLocal() as session:
        job = await upsert_job(session, record)
        items = (await session.execute(
            select(RelatedJob).where(RelatedJob.parent_job_id == job.id)
        )).scalars().all()
        assert len(items) == 1
        assert items[0].canonical_related_job_url == "https://www.linkedin.com/jobs/view/100/"

    await engine.dispose()
