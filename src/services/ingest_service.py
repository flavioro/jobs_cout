import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.base import BaseAdapter
from src.adapters.factory import AdapterFactory
from src.core.compare import compare_optional_hint
from src.core.config import get_settings
from src.schemas.jobs import ConfirmationPayload, IngestUrlRequest, IngestUrlResponse
from src.services.persistence_service import save_blocked_job, upsert_job
from src.utils.storage import save_raw_html
from src.utils.text import find_blocking_keyword

log = structlog.get_logger()


async def ingest_linkedin_request_with_adapter(
    request: IngestUrlRequest,
    session: AsyncSession,
    adapter: BaseAdapter,
) -> IngestUrlResponse:
    logger = log.bind(url=request.url, source="linkedin")
    logger.info("ingest.started")

    raw_page = await adapter.fetch(request.url)
    payload = adapter.extract(raw_page)
    record = adapter.normalize(payload, request)

    settings = get_settings()
    blocked_word = find_blocking_keyword(record.title, settings.parsed_title_blocklist)

    if blocked_word:
        reason_text = f"Palavra bloqueada: '{blocked_word}'"
        logger.info("job.blocked", reason=reason_text, title=record.title)

        await save_blocked_job(
            session=session,
            source=record.source.value,
            url=record.url,
            title=record.title,
            company=record.company,
            block_reason=reason_text,
        )

        return IngestUrlResponse(
            status="blocked",
            source=record.source.value,
            job_id=None,
            block_reason=reason_text,
        )

    raw_html_path = save_raw_html(
        html=raw_page.html,
        source="linkedin",
        canonical_url=record.canonical_url,
    )
    record = record.model_copy(update={"raw_html_path": raw_html_path})

    job = await upsert_job(session, record)

    if not job:
        logger.warning("ingest_linkedin_request.rejected", url=record.url, reason="missing_core_fields")
        return IngestUrlResponse(
            status="rejected",
            source=record.source.value,
            job_id=None,
            parser_version=record.parser_version,
            confirmation=ConfirmationPayload(
                title="missing",
                company="missing",
                location_raw="missing",
                is_easy_apply="missing",
                seniority_hint="missing",
                workplace_type="missing",
            ),
            job=None,
        )

    confirmation = ConfirmationPayload(
        title=compare_optional_hint(request.title, record.title),
        company=compare_optional_hint(request.company, record.company),
        location_raw=compare_optional_hint(request.location_raw, record.location_raw),
        is_easy_apply=compare_optional_hint(request.is_easy_apply, record.is_easy_apply),
        seniority_hint=compare_optional_hint(request.seniority_hint, record.seniority_raw),
        workplace_type=compare_optional_hint(
            request.workplace_type.value if request.workplace_type else None,
            record.workplace_type.value if record.workplace_type else None,
        ),
    )

    logger.info(
        "ingest.completed",
        status=record.status.value,
        availability_status=record.availability_status.value,
        related_jobs_count=len(record.related_jobs),
        job_id=job.id,
    )

    return IngestUrlResponse(
        status=record.status.value,
        source=record.source.value,
        job_id=job.id,
        parser_version=record.parser_version,
        confirmation=confirmation,
        job={
            "title": record.title,
            "company": record.company,
            "location_raw": record.location_raw,
            "is_easy_apply": record.is_easy_apply,
            "seniority_normalized": record.seniority_normalized.value if record.seniority_normalized else None,
            "workplace_type": record.workplace_type.value if record.workplace_type else None,
            "availability_status": record.availability_status.value,
            "closed_reason": record.closed_reason.value if record.closed_reason else None,
            "apply_url": record.apply_url,
            "related_jobs_count": len(record.related_jobs),
        },
    )


async def ingest_linkedin_request(request: IngestUrlRequest, session: AsyncSession) -> IngestUrlResponse:
    adapter = AdapterFactory.get_adapter(request.url)
    return await ingest_linkedin_request_with_adapter(request, session, adapter)


async def ingest_url(request: IngestUrlRequest, session: AsyncSession) -> IngestUrlResponse:
    return await ingest_linkedin_request(request, session)
