from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.linkedin.adapter import LinkedInAdapter
from src.adapters.linkedin.fetcher import LinkedInBrowserSession
from src.db.models import JobCandidate
from src.schemas.jobs import IngestUrlRequest
from src.services.ingest_service import ingest_linkedin_request_with_adapter
from src.services.linkedin_search_collection_service import collect_jobs_from_search_urls, summarize_cards

TERMINAL_PROCESSING_STATUSES = {"processed"}


def canonical_candidate_url(url: str | None) -> str:
    if not url:
        return ""
    value = str(url).strip()
    return value.split("?", 1)[0].rstrip("/") + "/"


def _candidate_key(card: dict[str, Any]) -> tuple[str | None, str]:
    return card.get("linkedin_job_id"), canonical_candidate_url(card.get("linkedin_job_url"))


def _is_closed_or_invalid(card: dict[str, Any]) -> bool:
    return (
        card.get("availability_status") == "closed"
        or card.get("extraction_status") in {"closed", "invalid"}
        or not card.get("linkedin_job_url")
    )


def _initial_processing_status(card: dict[str, Any], existing: JobCandidate | None = None) -> str:
    if existing and existing.processing_status in TERMINAL_PROCESSING_STATUSES:
        return existing.processing_status
    if _is_closed_or_invalid(card):
        return "skipped"
    if existing and existing.processing_status == "failed":
        return "failed"
    return "pending"


async def find_candidate_for_card(session: AsyncSession, card: dict[str, Any], source: str = "linkedin") -> JobCandidate | None:
    source_job_id, canonical_url = _candidate_key(card)
    clauses = []
    if source_job_id:
        clauses.append(JobCandidate.source_job_id == source_job_id)
    if canonical_url:
        clauses.append(JobCandidate.canonical_source_url == canonical_url)
    if not clauses:
        return None
    result = await session.execute(select(JobCandidate).where(JobCandidate.source == source, or_(*clauses)))
    return result.scalars().first()


async def upsert_job_candidates_from_cards(
    session: AsyncSession,
    cards: list[dict[str, Any]],
    *,
    source: str = "linkedin",
    commit: bool = True,
) -> dict[str, Any]:
    created = 0
    updated = 0
    skipped_without_url = 0
    items: list[dict[str, Any]] = []

    for index, card in enumerate(cards, start=1):
        source_url = card.get("linkedin_job_url")
        canonical_url = canonical_candidate_url(source_url)
        if not canonical_url:
            skipped_without_url += 1
            items.append({"row_number": index, "status": "skipped", "error": "missing_url"})
            continue

        existing = await find_candidate_for_card(session, card, source=source)
        processing_status = _initial_processing_status(card, existing)
        now = datetime.now(timezone.utc)
        values = {
            "source": source,
            "source_job_id": card.get("linkedin_job_id"),
            "source_url": source_url,
            "canonical_source_url": canonical_url,
            "source_search_url": card.get("source_search_url"),
            "title": card.get("title"),
            "company": card.get("company"),
            "location_raw": card.get("location_raw"),
            "workplace_type": card.get("workplace_type") or card.get("workplace_type_raw"),
            "employment_type_raw": card.get("employment_type_raw"),
            "seniority_hint": card.get("seniority_hint"),
            "is_easy_apply": card.get("is_easy_apply"),
            "availability_status": card.get("availability_status"),
            "availability_reason": card.get("availability_reason"),
            "extraction_status": card.get("extraction_status"),
            "missing_fields": card.get("missing_fields") if isinstance(card.get("missing_fields"), list) else None,
            "detail_completed": bool(card.get("detail_completed")),
            "detail_url_opened": bool(card.get("detail_url_opened")),
            "detail_completion_source": card.get("detail_completion_source"),
            "detail_error": card.get("detail_error"),
            "raw_card_text": card.get("card_text_raw"),
            "raw_detail_text": card.get("detail_text"),
            "raw_payload_json": dict(card),
            "processing_status": processing_status,
            "updated_at": now,
        }

        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            candidate = existing
            updated += 1
            action = "updated"
        else:
            candidate = JobCandidate(**values, collected_at=now)
            session.add(candidate)
            created += 1
            action = "created"

        items.append({
            "row_number": index,
            "candidate_id": candidate.id,
            "source_job_id": values["source_job_id"],
            "url": source_url,
            "title": values["title"],
            "company": values["company"],
            "processing_status": processing_status,
            "action": action,
        })

    if commit:
        await session.commit()

    return {
        "status": "completed",
        "source": source,
        "total_cards": len(cards),
        "created_count": created,
        "updated_count": updated,
        "skipped_count": skipped_without_url,
        "items": items,
    }


async def collect_linkedin_search_jobs_to_candidates(
    *,
    session: AsyncSession,
    search_items: list[dict] | None = None,
    max_jobs_per_url: int | None = None,
    export_xlsx: bool | None = False,
    export_xlsx_path: str | None = None,
) -> dict[str, Any]:
    cards = await collect_jobs_from_search_urls(
        search_items,
        max_jobs_per_url=max_jobs_per_url,
        export_xlsx=export_xlsx,
        export_xlsx_path=export_xlsx_path,
    )
    upsert_result = await upsert_job_candidates_from_cards(session, cards)
    card_summary = summarize_cards(cards)
    return {
        "status": "completed",
        "source": "linkedin_search",
        "collected_count": len(cards),
        "complete_count": card_summary["complete"],
        "partial_count": card_summary["partial"],
        "closed_count": card_summary["closed"],
        "invalid_count": card_summary["invalid"],
        "created_count": upsert_result["created_count"],
        "updated_count": upsert_result["updated_count"],
        "skipped_count": upsert_result["skipped_count"],
        "items": upsert_result["items"],
    }


async def list_job_candidates(
    session: AsyncSession,
    *,
    source: str | None = "linkedin",
    processing_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[JobCandidate]]:
    clauses = []
    if source:
        clauses.append(JobCandidate.source == source)
    if processing_status:
        clauses.append(JobCandidate.processing_status == processing_status)
    stmt = select(JobCandidate).where(*clauses).order_by(JobCandidate.collected_at.desc())
    result = await session.execute(stmt.offset(offset).limit(limit))
    items = list(result.scalars().all())
    total_result = await session.execute(select(JobCandidate).where(*clauses))
    total = len(total_result.scalars().all())
    return total, items


async def process_pending_job_candidates(
    *,
    session: AsyncSession,
    source: str = "linkedin",
    limit: int = 20,
    dry_run: bool = False,
    retry_failed: bool = False,
    skip_closed: bool = True,
    continue_on_error: bool = True,
    browser_session_factory=LinkedInBrowserSession,
    ingest_func=ingest_linkedin_request_with_adapter,
) -> dict[str, Any]:
    statuses = ["pending"]
    if retry_failed:
        statuses.append("failed")
    result = await session.execute(
        select(JobCandidate)
        .where(JobCandidate.source == source, JobCandidate.processing_status.in_(statuses))
        .order_by(JobCandidate.collected_at.asc())
        .limit(limit)
    )
    candidates = list(result.scalars().all())

    items: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    if dry_run:
        for candidate in candidates:
            should_skip, reason = _should_skip_candidate(candidate, skip_closed=skip_closed)
            items.append(_candidate_result_item(candidate, ok=False, skipped=True, result_status="dry_run", error=reason if should_skip else None))
            skipped_count += 1
        return _processing_summary("dry_run", dry_run, candidates, success_count, failed_count, skipped_count, items)

    async with browser_session_factory() as browser_session:
        adapter = LinkedInAdapter(fetcher=browser_session.fetch)
        for candidate in candidates:
            should_skip, reason = _should_skip_candidate(candidate, skip_closed=skip_closed)
            if should_skip:
                candidate.processing_status = "skipped"
                candidate.processing_error = reason
                candidate.updated_at = datetime.now(timezone.utc)
                skipped_count += 1
                items.append(_candidate_result_item(candidate, ok=False, skipped=True, result_status="skipped", error=reason))
                continue

            candidate.processing_status = "processing"
            candidate.processing_attempts += 1
            candidate.processing_error = None
            await session.flush()

            try:
                response = await ingest_func(_candidate_to_ingest_request(candidate), session, adapter)
                ok = response.status not in {"error", "rejected", "blocked"} and response.job_id is not None
                candidate.updated_at = datetime.now(timezone.utc)
                if ok:
                    candidate.processing_status = "processed"
                    candidate.processing_error = None
                    candidate.job_id = response.job_id
                    candidate.processed_at = datetime.now(timezone.utc)
                    success_count += 1
                else:
                    candidate.processing_status = "failed"
                    candidate.processing_error = response.block_reason or response.status
                    failed_count += 1
                items.append(_candidate_result_item(candidate, ok=ok, skipped=False, result_status=response.status, error=candidate.processing_error))
            except Exception as exc:
                candidate.processing_status = "failed"
                candidate.processing_error = str(exc)
                candidate.updated_at = datetime.now(timezone.utc)
                failed_count += 1
                items.append(_candidate_result_item(candidate, ok=False, skipped=False, result_status="error", error=str(exc)))
                if not continue_on_error:
                    break

    await session.commit()
    return _processing_summary("completed", dry_run, candidates, success_count, failed_count, skipped_count, items)


def _should_skip_candidate(candidate: JobCandidate, *, skip_closed: bool) -> tuple[bool, str | None]:
    if not candidate.source_url:
        return True, "missing_url"
    if candidate.extraction_status == "invalid":
        return True, "invalid_candidate"
    if skip_closed and (candidate.availability_status == "closed" or candidate.extraction_status == "closed"):
        return True, "closed_candidate_skipped"
    return False, None


def _candidate_to_ingest_request(candidate: JobCandidate) -> IngestUrlRequest:
    return IngestUrlRequest(
        url=candidate.source_url,
        title=candidate.title,
        company=candidate.company,
        location_raw=candidate.location_raw,
        is_easy_apply=candidate.is_easy_apply,
        seniority_hint=candidate.seniority_hint,
        workplace_type=candidate.workplace_type,
    )


def _candidate_result_item(candidate: JobCandidate, *, ok: bool, skipped: bool, result_status: str, error: str | None) -> dict[str, Any]:
    return {
        "candidate_id": candidate.id,
        "source_job_id": candidate.source_job_id,
        "url": candidate.source_url,
        "title": candidate.title,
        "company": candidate.company,
        "processing_status": candidate.processing_status,
        "ok": ok,
        "skipped": skipped,
        "job_id": candidate.job_id,
        "result_status": result_status,
        "error": error,
    }


def _processing_summary(status: str, dry_run: bool, candidates: list[JobCandidate], success_count: int, failed_count: int, skipped_count: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": status,
        "source": "job_candidates",
        "dry_run": dry_run,
        "selected_count": len(candidates),
        "processed": len([item for item in items if not item.get("skipped")]),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "items": items,
    }
