from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.db.models import Job, RelatedJob, BlockedJob
from src.schemas.jobs import JobRecordSchema, RelatedJobListRead, RelatedJobRead, RelatedJobSchema
# Adicionei a importação do EnglishLevel
from src.core.enums import EnglishLevel

logger = structlog.get_logger(__name__)


async def upsert_job(session: AsyncSession, record: JobRecordSchema) -> Job:
    result = await session.execute(
        select(Job).where(Job.canonical_url == record.canonical_url).where(Job.fingerprint == record.fingerprint)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.external_id = record.external_id
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
        await _sync_related_rows_for_job(session, existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    job = Job(
        source=record.source.value,
        external_id=record.external_id,
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
    await _sync_related_rows_for_job(session, job)
    await session.commit()
    await session.refresh(job)
    return job


async def _replace_related_jobs(session: AsyncSession, parent_job_id: str, record: JobRecordSchema) -> None:
    await session.execute(delete(RelatedJob).where(RelatedJob.parent_job_id == parent_job_id))
    seen_canonical_urls: set[str] = set()

    for item in record.related_jobs:
        if not item.related_external_id:
            logger.warning(
                "related_job_missing_external_id_skipped",
                parent_job_id=parent_job_id,
                related_url=item.related_url,
                title=item.title,
            )
            continue

        canonical_related_job_url = item.canonical_related_job_url
        if not canonical_related_job_url:
            logger.warning(
                "related_job_missing_canonical_url_skipped",
                parent_job_id=parent_job_id,
                related_external_id=item.related_external_id,
                related_url=item.related_url,
                title=item.title,
            )
            continue

        if canonical_related_job_url in seen_canonical_urls:
            continue
        seen_canonical_urls.add(canonical_related_job_url)

        matching_job = await _find_existing_job_for_related(session, item)
        existing_global = await session.scalar(
            select(RelatedJob).where(RelatedJob.canonical_related_job_url == canonical_related_job_url)
        )
        if existing_global:
            _apply_related_job_values(existing_global, parent_job_id, item, matching_job)
            continue

        related_job = RelatedJob(
            parent_job_id=parent_job_id,
            resolved_job_id=matching_job.id if matching_job else None,
            related_external_id=item.related_external_id,
            related_url=item.related_url,
            canonical_related_job_url=canonical_related_job_url,
            title=item.title,
            company=item.company,
            location_raw=item.location_raw,
            workplace_type=item.workplace_type.value if item.workplace_type else None,
            is_easy_apply=item.is_easy_apply,
            posted_text_raw=item.posted_text_raw,
            candidate_signal_raw=item.candidate_signal_raw,
            is_verified=item.is_verified,
            is_promoted_to_job=matching_job is not None,
            promotion_status="promoted" if matching_job else "pending",
            last_promoted_at=datetime.now(timezone.utc) if matching_job else None,
        )
        session.add(related_job)


async def _find_existing_job_for_related(session: AsyncSession, item: RelatedJobSchema) -> Job | None:
    if item.canonical_related_job_url:
        existing_by_canonical = await session.scalar(
            select(Job)
            .where(Job.source == "linkedin")
            .where(Job.canonical_url == item.canonical_related_job_url)
            .order_by(Job.created_at.desc())
        )
        if existing_by_canonical:
            return existing_by_canonical

    if item.related_external_id:
        return await session.scalar(
            select(Job)
            .where(Job.source == "linkedin")
            .where(Job.external_id == item.related_external_id)
            .order_by(Job.created_at.desc())
        )
    return None


def _apply_related_job_values(
    existing_global: RelatedJob,
    parent_job_id: str,
    item: RelatedJobSchema,
    matching_job: Job | None,
) -> None:
    existing_global.parent_job_id = parent_job_id
    existing_global.related_external_id = item.related_external_id
    existing_global.related_url = item.related_url
    existing_global.canonical_related_job_url = item.canonical_related_job_url or existing_global.canonical_related_job_url
    existing_global.title = item.title
    existing_global.company = item.company
    existing_global.location_raw = item.location_raw
    existing_global.workplace_type = item.workplace_type.value if item.workplace_type else None
    existing_global.is_easy_apply = item.is_easy_apply
    existing_global.posted_text_raw = item.posted_text_raw
    existing_global.candidate_signal_raw = item.candidate_signal_raw
    existing_global.is_verified = item.is_verified
    if matching_job:
        existing_global.resolved_job_id = matching_job.id
        existing_global.is_promoted_to_job = True
        existing_global.promotion_status = "promoted"
        existing_global.last_promotion_error = None
        existing_global.last_promoted_at = datetime.now(timezone.utc)
    elif not existing_global.is_promoted_to_job:
        existing_global.resolved_job_id = None
        existing_global.promotion_status = "pending"


async def _sync_related_rows_for_job(session: AsyncSession, job: Job) -> None:
    related_row = await session.scalar(
        select(RelatedJob).where(RelatedJob.canonical_related_job_url == job.canonical_url)
    )
    if not related_row:
        return

    related_row.resolved_job_id = job.id
    related_row.is_promoted_to_job = True
    related_row.promotion_status = "promoted"
    related_row.last_promotion_error = None
    related_row.last_promoted_at = datetime.now(timezone.utc)


async def list_related_jobs(
    session: AsyncSession,
    parent_job_id: str | None = None,
    company: str | None = None,
    workplace_type: str | None = None,
    is_easy_apply: bool | None = None,
    promotion_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> RelatedJobListRead:
    filters = []
    if parent_job_id:
        filters.append(RelatedJob.parent_job_id == parent_job_id)
    if company:
        filters.append(RelatedJob.company == company)
    if workplace_type:
        filters.append(RelatedJob.workplace_type == workplace_type)
    if is_easy_apply is not None:
        filters.append(RelatedJob.is_easy_apply == is_easy_apply)
    if promotion_status:
        filters.append(RelatedJob.promotion_status == promotion_status)

    total_stmt = select(func.count()).select_from(RelatedJob)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = select(RelatedJob).order_by(RelatedJob.created_at.desc()).limit(limit).offset(offset)
    if filters:
        stmt = stmt.where(*filters)
    items = (await session.execute(stmt)).scalars().all()

    return RelatedJobListRead(
        items=[RelatedJobRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )

async def save_blocked_job(
    session: AsyncSession,
    source: str,
    url: str,
    title: str | None,
    company: str | None,
    block_reason: str,
) -> BlockedJob:
    # Verifica se já existe
    stmt = select(BlockedJob).where(BlockedJob.url == url)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    
    if existing:
        existing.block_reason = block_reason # Atualiza o motivo se necessário
        await session.commit()
        return existing

    blocked_job = BlockedJob(
        source=source,
        url=url,
        title=title,
        company=company,
        block_reason=block_reason,
    )
    session.add(blocked_job)
    await session.commit()
    return blocked_job


# --- NOVOS MÉTODOS PARA A FASE 2 (IA ENRICHMENT) ---

async def get_pending_jobs_for_enrichment(session: AsyncSession, limit: int = 10) -> list[Job]:
    """Busca vagas que foram processadas com sucesso, mas ainda não passaram pela IA."""
    stmt = (
        select(Job)
        .where(Job.status == "success")
        .where(Job.fit_score.is_(None))
        .where(Job.description_text.is_not(None))
        .order_by(Job.created_at.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_job_ai_enrichment(
    session: AsyncSession, 
    job_id: str, 
    fit_score: int, 
    fit_rationale: str, 
    skills: list[str], 
    salary_raw: str | None,
    english_level: EnglishLevel
) -> Job | None:
    """Atualiza um Job existente com os resultados gerados pela Groq LLM."""
    job = await session.scalar(select(Job).where(Job.id == job_id))
    if not job:
        return None
        
    job.fit_score = fit_score
    job.fit_rationale = fit_rationale
    job.skills = skills
    job.salary_raw = salary_raw
    job.english_level = english_level.value
    job.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
    await session.refresh(job)
    return job

async def delete_job(session: AsyncSession, job_id: str) -> bool:
    """Remove uma vaga da tabela principal (utilizado se for bloqueada tardiamente)."""
    try:
        stmt = delete(Job).where(Job.id == job_id)
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as e:
        logger.error("delete_job.error", job_id=job_id, error=str(e))
        return False