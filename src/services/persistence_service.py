from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Job, RelatedJob
from src.schemas.jobs import JobRecordSchema, RelatedJobListRead, RelatedJobRead


async def upsert_job(session: AsyncSession, record: JobRecordSchema) -> Job:
    result = await session.execute(
        select(Job).where(Job.canonical_url == record.canonical_url).where(Job.fingerprint == record.fingerprint)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.title = record.title
        existing.company = record.company
        existing.location_raw = record.location_raw
        existing.workplace_type = record.workplace_type.value if record.workplace_type else None
        existing.seniority_raw = record.seniority_raw
        existing.seniority_normalized = record.seniority_normalized.value if record.seniority_normalized else None
        existing.is_easy_apply = record.is_easy_apply
        existing.availability_status = record.availability_status.value if record.availability_status else None
        existing.closed_reason = record.closed_reason.value if record.closed_reason else None
        existing.description_text = record.description_text
        existing.apply_url = record.apply_url
        existing.template_source = record.template_source
        existing.parser_used = record.parser_used
        existing.parser_version = record.parser_version
        existing.status = record.status.value
        existing.raw_html_path = record.raw_html_path
        existing.collected_at = record.collected_at
        await _replace_related_jobs(session, existing.id, record)
        await session.commit()
        await session.refresh(existing)
        return existing

    job = Job(
        source=record.source.value,
        url=record.url,
        canonical_url=record.canonical_url,
        apply_url=record.apply_url,
        title=record.title,
        company=record.company,
        location_raw=record.location_raw,
        workplace_type=record.workplace_type.value if record.workplace_type else None,
        seniority_raw=record.seniority_raw,
        seniority_normalized=record.seniority_normalized.value if record.seniority_normalized else None,
        is_easy_apply=record.is_easy_apply,
        availability_status=record.availability_status.value if record.availability_status else None,
        closed_reason=record.closed_reason.value if record.closed_reason else None,
        description_text=record.description_text,
        template_source=record.template_source,
        parser_used=record.parser_used,
        parser_version=record.parser_version,
        status=record.status.value,
        fingerprint=record.fingerprint,
        raw_html_path=record.raw_html_path,
        collected_at=record.collected_at,
    )
    session.add(job)
    await session.flush()
    await _replace_related_jobs(session, job.id, record)
    await session.commit()
    await session.refresh(job)
    return job


async def _replace_related_jobs(session: AsyncSession, parent_job_id: str, record: JobRecordSchema) -> None:
    await session.execute(delete(RelatedJob).where(RelatedJob.parent_job_id == parent_job_id))
    seen_canonical_urls: set[str | None] = set()
    for item in record.related_jobs:
        canonical_related_job_url = item.canonical_related_job_url
        if canonical_related_job_url in seen_canonical_urls:
            continue
        seen_canonical_urls.add(canonical_related_job_url)
        session.add(
            RelatedJob(
                parent_job_id=parent_job_id,
                related_external_id=item.related_external_id,
                related_url=item.related_url,
                canonical_related_job_url=item.canonical_related_job_url,
                title=item.title,
                company=item.company,
                location_raw=item.location_raw,
                workplace_type=item.workplace_type.value if item.workplace_type else None,
                is_easy_apply=item.is_easy_apply,
                posted_text_raw=item.posted_text_raw,
                candidate_signal_raw=item.candidate_signal_raw,
                is_verified=item.is_verified,
            )
        )


async def list_related_jobs(
    session: AsyncSession,
    *,
    parent_job_id: str | None = None,
    company: str | None = None,
    workplace_type: str | None = None,
    is_easy_apply: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> RelatedJobListRead:
    filters = []

    if parent_job_id:
        filters.append(RelatedJob.parent_job_id == parent_job_id)
    if company:
        filters.append(RelatedJob.company.ilike(f"%{company}%"))
    if workplace_type:
        filters.append(RelatedJob.workplace_type == workplace_type)
    if is_easy_apply is not None:
        filters.append(RelatedJob.is_easy_apply == is_easy_apply)

    base_query = select(RelatedJob)
    count_query = select(func.count()).select_from(RelatedJob)

    if filters:
        base_query = base_query.where(*filters)
        count_query = count_query.where(*filters)

    base_query = base_query.order_by(RelatedJob.created_at.desc()).limit(limit).offset(offset)

    total = (await session.execute(count_query)).scalar_one()
    rows = (await session.execute(base_query)).scalars().all()

    items = [RelatedJobRead.model_validate(row) for row in rows]
    return RelatedJobListRead(items=items, total=total, limit=limit, offset=offset)
