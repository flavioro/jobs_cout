from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.adapters.linkedin.search_extractor import LinkedInSearchExtractor, LinkedInSearchJobCard
from src.adapters.linkedin.search_fetcher import LinkedInSearchSession, load_search_urls_from_file
from src.core.config import get_settings
from src.utils.xlsx_export import write_dicts_to_xlsx

CARD_XLSX_HEADERS = [
    "linkedin_job_id",
    "linkedin_job_url",
    "title",
    "company",
    "location_raw",
    "workplace_type",
    "seniority_hint",
    "is_easy_apply",
    "availability_status",
    "availability_reason",
    "extraction_status",
    "missing_fields",
    "detail_completed",
    "detail_url_opened",
    "detail_completion_source",
    "detail_error",
    "card_text_raw",
    "detail_text",
    "workplace_type_raw",
    "employment_type_raw",
    "source_search_url",
    "collected_at",
]


def export_search_cards_to_xlsx(cards: list[dict], path: str | None = None) -> str:
    settings = get_settings()
    export_path = path or settings.linkedin_search_export_xlsx_path
    normalized_rows = []
    for card in cards:
        row = {header: card.get(header) for header in CARD_XLSX_HEADERS}
        if isinstance(row.get("missing_fields"), list):
            row["missing_fields"] = ", ".join(row["missing_fields"])
        normalized_rows.append(row)
    return write_dicts_to_xlsx(export_path, normalized_rows, CARD_XLSX_HEADERS)


async def collect_jobs_from_search_urls(
    search_items: list[dict] | None = None,
    *,
    max_jobs_per_url: int | None = None,
    session_factory=LinkedInSearchSession,
    extractor: LinkedInSearchExtractor | None = None,
    export_xlsx_path: str | None = None,
    export_xlsx: bool | None = None,
) -> list[dict]:
    settings = get_settings()
    extractor = extractor or LinkedInSearchExtractor()
    if search_items is None:
        search_items = load_search_urls_from_file(settings.linkedin_search_urls_path)

    max_per_url = max_jobs_per_url or settings.linkedin_search_card_limit_per_url
    collected: list[dict] = []
    seen_urls: set[str] = set()

    async with session_factory() as session:
        for item in search_items:
            if not item.get("enabled", True):
                continue
            cards = await _collect_cards_for_url(session, extractor, item["url"])
            for card in cards[:max_per_url]:
                card_dict = _card_to_dict(card)
                url = card_dict.get("linkedin_job_url")
                if not url or url in seen_urls:
                    continue
                collected.append(card_dict)
                seen_urls.add(url)

    should_export = settings.linkedin_search_export_xlsx_enabled if export_xlsx is None else export_xlsx
    if should_export:
        export_search_cards_to_xlsx(collected, export_xlsx_path)

    return collected


async def _collect_cards_for_url(session, extractor: LinkedInSearchExtractor, url: str) -> list[LinkedInSearchJobCard]:
    if hasattr(session, "fetch_search_cards"):
        raw_cards = await session.fetch_search_cards(url)
        cards: list[LinkedInSearchJobCard] = []
        for payload in raw_cards:
            card = extractor.from_browser_payload(payload, source_search_url=url)
            if card is not None:
                cards.append(card)
        if cards:
            return cards
    html = await session.fetch_search_page(url)
    return extractor.extract(html, source_search_url=url)


def _card_to_dict(card: LinkedInSearchJobCard | dict[str, Any]) -> dict:
    if isinstance(card, LinkedInSearchJobCard):
        return asdict(card)
    return dict(card)


def summarize_cards(cards: list[dict]) -> dict:
    by_status: dict[str, int] = {}
    by_availability: dict[str, int] = {}
    detail_completed_count = 0
    detail_url_opened_count = 0
    for card in cards:
        by_status[card.get("extraction_status") or "unknown"] = by_status.get(card.get("extraction_status") or "unknown", 0) + 1
        by_availability[card.get("availability_status") or "unknown"] = by_availability.get(card.get("availability_status") or "unknown", 0) + 1
        if card.get("detail_completed"):
            detail_completed_count += 1
        if card.get("detail_url_opened"):
            detail_url_opened_count += 1
    return {
        "total": len(cards),
        "complete": by_status.get("complete", 0),
        "partial": by_status.get("partial", 0),
        "closed": by_status.get("closed", 0),
        "invalid": by_status.get("invalid", 0),
        "detail_completed": detail_completed_count,
        "detail_url_opened": detail_url_opened_count,
        "availability": by_availability,
    }
