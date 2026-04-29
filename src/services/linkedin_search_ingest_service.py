from __future__ import annotations

from src.adapters.linkedin.adapter import LinkedInAdapter
try:
    from src.adapters.linkedin.fetcher import LinkedInBrowserSession
except ImportError:  # Compatibilidade com versões antigas do fetcher.
    from src.adapters.linkedin.fetcher import fetch_linkedin_page

    class LinkedInBrowserSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def fetch(self, url: str):
            return await fetch_linkedin_page(url)
from src.core.config import get_settings
from src.schemas.jobs import IngestUrlRequest
from src.services.ingest_service import ingest_linkedin_request_with_adapter
from src.services.linkedin_search_collection_service import (
    collect_jobs_from_search_urls,
    export_search_cards_to_xlsx,
    summarize_cards,
)


async def collect_and_ingest_search_jobs(
    *,
    session,
    search_items: list[dict] | None = None,
    max_jobs_per_url: int | None = None,
    continue_on_error: bool = True,
    skip_closed: bool | None = None,
    export_xlsx: bool | None = None,
    export_xlsx_path: str | None = None,
) -> dict:
    settings = get_settings()
    effective_skip_closed = settings.linkedin_search_skip_closed if skip_closed is None else skip_closed
    collected = await collect_jobs_from_search_urls(
        search_items,
        max_jobs_per_url=max_jobs_per_url,
        export_xlsx=False,
    )
    cards_xlsx_path = None
    should_export = settings.linkedin_search_export_xlsx_enabled if export_xlsx is None else export_xlsx
    if should_export:
        cards_xlsx_path = export_search_cards_to_xlsx(collected, export_xlsx_path)

    items: list[dict] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    async with LinkedInBrowserSession() as browser_session:
        adapter = LinkedInAdapter(fetcher=browser_session.fetch)
        for index, card in enumerate(collected, start=1):
            if card.get("extraction_status") == "invalid" or not card.get("linkedin_job_url"):
                skipped_count += 1
                items.append(_skipped_item(index, card, "invalid_card"))
                continue
            if effective_skip_closed and card.get("availability_status") == "closed":
                skipped_count += 1
                items.append(_skipped_item(index, card, "closed_card_skipped"))
                continue

            request = IngestUrlRequest(
                url=card["linkedin_job_url"],
                title=card.get("title"),
                company=card.get("company"),
                location_raw=card.get("location_raw"),
                is_easy_apply=card.get("is_easy_apply"),
                seniority_hint=card.get("seniority_hint"),
                workplace_type=card.get("workplace_type"),
            )
            try:
                response = await ingest_linkedin_request_with_adapter(request, session, adapter)
                ok = response.status in {"success", "updated", "blocked", "rejected", "open", "closed"}
                if ok and response.job_id:
                    success_count += 1
                else:
                    failed_count += 1
                items.append({
                    "row_number": index,
                    "linkedin_job_id": card.get("linkedin_job_id"),
                    "url": card["linkedin_job_url"],
                    "title": card.get("title"),
                    "company": card.get("company"),
                    "extraction_status": card.get("extraction_status"),
                    "availability_status": card.get("availability_status"),
                    "detail_completed": card.get("detail_completed"),
                    "detail_url_opened": card.get("detail_url_opened"),
                    "ok": ok,
                    "skipped": False,
                    "job_id": response.job_id,
                    "result_status": response.status,
                    "error": None if ok else response.block_reason,
                })
            except Exception as exc:
                failed_count += 1
                items.append({
                    "row_number": index,
                    "linkedin_job_id": card.get("linkedin_job_id"),
                    "url": card["linkedin_job_url"],
                    "title": card.get("title"),
                    "company": card.get("company"),
                    "extraction_status": card.get("extraction_status"),
                    "availability_status": card.get("availability_status"),
                    "detail_completed": card.get("detail_completed"),
                    "detail_url_opened": card.get("detail_url_opened"),
                    "ok": False,
                    "skipped": False,
                    "job_id": None,
                    "result_status": "error",
                    "error": str(exc),
                })
                if not continue_on_error:
                    break

    card_summary = summarize_cards(collected)
    return {
        "status": "completed",
        "source": "linkedin_search",
        "total_search_urls": len([x for x in (search_items or []) if x.get("enabled", True)]) if search_items is not None else None,
        "collected_count": len(collected),
        "complete_count": card_summary["complete"],
        "partial_count": card_summary["partial"],
        "closed_count": card_summary["closed"],
        "invalid_count": card_summary["invalid"],
        "detail_completed_count": card_summary.get("detail_completed", 0),
        "detail_url_opened_count": card_summary.get("detail_url_opened", 0),
        "processed": len([item for item in items if not item.get("skipped")]),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "cards_xlsx_path": cards_xlsx_path,
        "items": items,
    }


def _skipped_item(index: int, card: dict, reason: str) -> dict:
    return {
        "row_number": index,
        "linkedin_job_id": card.get("linkedin_job_id"),
        "url": card.get("linkedin_job_url") or "",
        "title": card.get("title"),
        "company": card.get("company"),
        "extraction_status": card.get("extraction_status"),
        "availability_status": card.get("availability_status"),
        "detail_completed": card.get("detail_completed"),
        "detail_url_opened": card.get("detail_url_opened"),
        "ok": False,
        "skipped": True,
        "job_id": None,
        "result_status": "skipped",
        "error": reason,
    }
