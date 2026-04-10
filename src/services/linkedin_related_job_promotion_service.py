from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Job, RelatedJob
from src.schemas.jobs import IngestUrlRequest, LinkedinPromotePendingRelatedJobsResponse
from src.services.ingest_service import ingest_linkedin_request

logger = structlog.get_logger(__name__)


async def promote_pending_linkedin_related_jobs(
    session: AsyncSession,
    limit: int = 10,
) -> LinkedinPromotePendingRelatedJobsResponse:
    stmt = (
        select(RelatedJob)
        .where(RelatedJob.promotion_status.in_(["pending", "failed"]))
        .order_by(RelatedJob.created_at.asc())
        .limit(limit)
    )
    related_jobs = (await session.execute(stmt)).scalars().all()

    summary_items: list[dict] = []
    promoted = 0
    already_resolved = 0
    failed = 0
    skipped = 0

    for related_job in related_jobs:
        if not related_job.canonical_related_job_url:
            related_job.promotion_status = "skipped"
            related_job.last_promotion_error = "missing canonical_related_job_url"
            skipped += 1
            summary_items.append(_build_summary_item(related_job, "skipped"))
            continue

        existing_job = await _find_existing_linkedin_job(session, related_job)
        if existing_job:
            _mark_promoted(related_job, existing_job.id)
            already_resolved += 1
            summary_items.append(_build_summary_item(related_job, "already_resolved"))
            continue

        related_job.promotion_attempts += 1

        try:
            response = await ingest_linkedin_request(
                request=IngestUrlRequest(url=related_job.canonical_related_job_url),
                session=session,
            )
            
            # --- NOVO: Lidar com o bloqueio do Porteiro ---
            if response.status == "blocked":
                related_job.promotion_status = "blocked"
                related_job.last_promotion_error = response.block_reason
                failed += 1
                summary_items.append(_build_summary_item(related_job, "blocked"))
                continue
            # ----------------------------------------------

            promoted_job = await _find_existing_linkedin_job(session, related_job)
            if promoted_job:
                _mark_promoted(related_job, promoted_job.id)
                promoted += 1
                summary_items.append(_build_summary_item(related_job, "promoted"))
            else:
                related_job.promotion_status = "failed"
                related_job.last_promotion_error = "Ingest completed but job not found in DB"
                failed += 1
                summary_items.append(_build_summary_item(related_job, "failed"))

        except Exception as e:
            logger.exception("promotion_failed", related_job_id=related_job.id, error=str(e))
            related_job.promotion_status = "failed"
            related_job.last_promotion_error = str(e)
            failed += 1
            summary_items.append(_build_summary_item(related_job, "failed"))

    await session.commit()

    return LinkedinPromotePendingRelatedJobsResponse(
        requested_limit=limit,
        processed=len(related_jobs),
        promoted=promoted,
        already_resolved=already_resolved,
        failed=failed,
        skipped=skipped,
        items=summary_items,
    )


async def _find_existing_linkedin_job(session: AsyncSession, related_job: RelatedJob) -> Job | None:
    job = await session.scalar(
        select(Job)
        .where(Job.source == "linkedin")
        .where(Job.canonical_url == related_job.canonical_related_job_url)
        .order_by(Job.created_at.desc())
    )
    if job:
        return job
    if related_job.related_external_id:
        return await session.scalar(
            select(Job)
            .where(Job.source == "linkedin")
            .where(Job.external_id == related_job.related_external_id)
            .order_by(Job.created_at.desc())
        )
    return None


def _mark_promoted(related_job: RelatedJob, resolved_job_id: str) -> None:
    related_job.resolved_job_id = resolved_job_id
    related_job.is_promoted_to_job = True
    related_job.promotion_status = "promoted"
    related_job.last_promotion_error = None
    related_job.last_promoted_at = datetime.now(timezone.utc)


def _build_summary_item(related_job: RelatedJob, action: str) -> dict:
    return {
        "related_job_id": related_job.id,
        "canonical_related_job_url": related_job.canonical_related_job_url,
        "action": action,
        "attempts": related_job.promotion_attempts,
        "error": related_job.last_promotion_error,
    }