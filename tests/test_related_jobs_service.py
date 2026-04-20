from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import UniqueConstraint, select
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
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/view/100/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related A",
                company="Company X",
                workplace_type="remote",
                is_easy_apply=True,
            ),
            RelatedJob(
                parent_job_id=job_id,
                related_external_id="101",
                related_url="https://www.linkedin.com/jobs/view/101/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                title="Related B",
                company="Company Y",
                workplace_type="hybrid",
                is_easy_apply=False,
            ),
            RelatedJob(
                parent_job_id=other_job_id,
                related_external_id="102",
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
async def test_upsert_job_deduplicates_related_jobs_by_global_canonical_url(tmp_path):
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
        description_text="Descrição falsa para passar na validação",
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


@pytest.mark.asyncio
async def test_related_jobs_unique_constraint_is_global_canonical_url(tmp_path):
    db_path = tmp_path / "related_jobs_unique.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    unique_constraints = [c for c in RelatedJob.__table__.constraints if isinstance(c, UniqueConstraint)]
    assert any(tuple(c.columns.keys()) == ("canonical_related_job_url",) for c in unique_constraints)

    await engine.dispose()


@pytest.mark.asyncio
async def test_related_jobs_can_still_insert_distinct_same_title_different_external_id(tmp_path):
    db_path = tmp_path / "related_jobs_distinct.db"
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
        description_text="Descrição falsa para passar na validação",
        parser_used="linkedin_css_bs4",
        parser_version="linkedin_v1.2",
        status=JobStatus.SUCCESS,
        availability_status=AvailabilityStatus.OPEN,
        collected_at=datetime.now(timezone.utc),
        fingerprint="fp-parent-2",
        related_jobs=[
            RelatedJobSchema(
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/collections/similar-jobs/?currentJobId=100",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Python Developer",
                company="Company X",
            ),
            RelatedJobSchema(
                related_external_id="101",
                related_url="https://www.linkedin.com/jobs/collections/similar-jobs/?currentJobId=101",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                title="Python Developer",
                company="Company Y",
            ),
        ],
    )

    async with SessionLocal() as session:
        job = await upsert_job(session, record)
        items = (await session.execute(select(RelatedJob).where(RelatedJob.parent_job_id == job.id))).scalars().all()
        assert len(items) == 2
        assert {item.related_external_id for item in items} == {"100", "101"}

    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_job_skips_related_jobs_without_related_external_id(tmp_path, capsys):
    db_path = tmp_path / "related_jobs_skip_missing_external.db"
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
        description_text="Descrição falsa para passar na validação",
        parser_used="linkedin_css_bs4",
        parser_version="linkedin_v1.2",
        status=JobStatus.SUCCESS,
        availability_status=AvailabilityStatus.OPEN,
        collected_at=datetime.now(timezone.utc),
        fingerprint="fp-parent-3",
        related_jobs=[
            RelatedJobSchema(
                related_external_id=None,
                related_url="https://www.linkedin.com/jobs/collections/similar-jobs/?trackingId=abc",
                canonical_related_job_url=None,
                title="Related without external id",
                company="Company X",
            ),
        ],
    )

    async with SessionLocal() as session:
        await upsert_job(session, record)
        items = (await session.execute(select(RelatedJob))).scalars().all()
        assert items == []

    captured = capsys.readouterr()
    assert "related_job_missing_external_id_skipped" in captured.out
    await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_job_links_existing_related_job_to_existing_job_record(tmp_path):
    db_path = tmp_path / "related_jobs_link_existing_job.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    resolved_job_id = str(uuid.uuid4())
    async with SessionLocal() as session:
        session.add(
            Job(
                id=resolved_job_id,
                source="linkedin",
                external_id="100",
                url="https://www.linkedin.com/jobs/view/100/",
                canonical_url="https://www.linkedin.com/jobs/view/100/",
                title="Resolved Job",
                company="Company X",
                parser_used="linkedin_css_bs4",
                parser_version="linkedin_v1.2",
                status="success",
                fingerprint="fp-existing-job",
                collected_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    record = JobRecordSchema(
        source=JobSource.LINKEDIN,
        external_id="999",
        url="https://www.linkedin.com/jobs/view/999/",
        canonical_url="https://www.linkedin.com/jobs/view/999/",
        title="Parent Job",
        company="Acme",
        description_text="Descrição falsa para passar na validação",
        parser_used="linkedin_css_bs4",
        parser_version="linkedin_v1.2",
        status=JobStatus.SUCCESS,
        availability_status=AvailabilityStatus.OPEN,
        collected_at=datetime.now(timezone.utc),
        fingerprint="fp-parent-link",
        related_jobs=[
            RelatedJobSchema(
                related_external_id="100",
                related_url="https://www.linkedin.com/jobs/view/100/",
                canonical_related_job_url="https://www.linkedin.com/jobs/view/100/",
                title="Related A",
                company="Company X",
            ),
        ],
    )

    async with SessionLocal() as session:
        parent_job = await upsert_job(session, record)
        item = (await session.execute(select(RelatedJob).where(RelatedJob.parent_job_id == parent_job.id))).scalar_one()
        assert item.resolved_job_id == resolved_job_id
        assert item.is_promoted_to_job is True
        assert item.promotion_status == "promoted"

    await engine.dispose()
