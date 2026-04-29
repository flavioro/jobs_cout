from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils.text import clean_location_raw, clean_text, map_seniority, map_workplace_type

CLOSED_MARKERS = (
    "expirado",
    "vaga expirada",
    "candidaturas encerradas",
    "candidatura encerrada",
    "no longer accepting applications",
    "job expired",
    "applications are closed",
    "não aceita mais candidaturas",
    "nao aceita mais candidaturas",
    "não está mais aceitando candidaturas",
    "nao esta mais aceitando candidaturas",
    "não recebe mais candidaturas",
    "nao recebe mais candidaturas",
)


@dataclass
class LinkedInSearchJobCard:
    linkedin_job_id: str
    linkedin_job_url: str
    title: str | None
    company: str | None
    location_raw: str | None
    workplace_type: str | None = None
    seniority_hint: str | None = None
    is_easy_apply: bool | None = None
    source_search_url: str | None = None
    collected_at: str | None = None
    availability_status: str = "unknown"
    availability_reason: str | None = None
    extraction_status: str = "partial"
    missing_fields: list[str] | None = None
    detail_completed: bool = False
    detail_url_opened: bool = False
    detail_completion_source: str | None = None
    detail_error: str | None = None
    card_text_raw: str | None = None
    detail_text: str | None = None
    workplace_type_raw: str | None = None
    employment_type_raw: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class LinkedInSearchExtractor:
    def extract(self, html: str, *, source_search_url: str | None = None) -> list[LinkedInSearchJobCard]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[LinkedInSearchJobCard] = []
        seen: set[str] = set()

        for node in soup.select("li[data-occludable-job-id], div.job-card-container[data-job-id], li.scaffold-layout__list-item"):
            job_id = clean_text(node.get("data-occludable-job-id") or node.get("data-job-id"))
            title_link = node.select_one("a.job-card-list__title--link, a.job-card-container__link, a[href*='/jobs/view/']")
            href = title_link.get("href") if title_link else None
            if not job_id:
                job_id = self._job_id_from_href(href)
            if not job_id or job_id in seen:
                continue

            title = self._extract_title(title_link)
            company_node = node.select_one(".artdeco-entity-lockup__subtitle span, .job-card-container__primary-description")
            company = clean_text(company_node.get_text(" ", strip=True) if company_node else None)

            location_node = node.select_one(".job-card-container__metadata-wrapper li span, .artdeco-entity-lockup__caption li span, .job-card-container__metadata-item")
            location_raw = clean_location_raw(location_node.get_text(" ", strip=True) if location_node else None)

            card_text_raw = clean_text(node.get_text(" ", strip=True)) or ""
            workplace = map_workplace_type(location_raw, card_text_raw)
            seniority = map_seniority(title, card_text_raw)
            is_easy_apply = True if re.search(r"candidatura simplificada|easy apply|candidate-se facilmente", card_text_raw, re.I) else None
            availability_status, availability_reason = self._detect_availability(card_text_raw)
            job_url = self._normalize_job_url(href, job_id)
            missing = self._missing_fields(title=title, company=company, location_raw=location_raw)
            extraction_status = self._status_for(job_url=job_url, availability_status=availability_status, missing_fields=missing)

            cards.append(LinkedInSearchJobCard(
                linkedin_job_id=job_id,
                linkedin_job_url=job_url,
                title=title,
                company=company,
                location_raw=location_raw,
                workplace_type=workplace.value if workplace else None,
                seniority_hint=seniority.value if seniority else None,
                is_easy_apply=is_easy_apply,
                source_search_url=source_search_url,
                collected_at=datetime.now(timezone.utc).isoformat(),
                availability_status=availability_status,
                availability_reason=availability_reason,
                extraction_status=extraction_status,
                missing_fields=missing,
                card_text_raw=card_text_raw,
            ))
            seen.add(job_id)

        return cards

    def from_browser_payload(self, payload: dict[str, Any], *, source_search_url: str | None = None) -> LinkedInSearchJobCard | None:
        job_id = clean_text(payload.get("linkedin_job_id")) or self._job_id_from_href(payload.get("linkedin_job_url"))
        if not job_id:
            return None
        job_url = self._normalize_job_url(payload.get("linkedin_job_url"), job_id)
        title = clean_text(payload.get("title"))
        company = clean_text(payload.get("company"))
        location_raw = clean_location_raw(payload.get("location_raw"))
        card_text_raw = clean_text(payload.get("card_text_raw") or payload.get("text"))
        detail_text = clean_text(payload.get("detail_text"))
        text_blob = " ".join(
            str(payload.get(key) or "")
            for key in (
                "card_text_raw",
                "text",
                "detail_text",
                "title",
                "company",
                "location_raw",
                "workplace_type_raw",
                "employment_type_raw",
            )
        )
        workplace = map_workplace_type(location_raw, text_blob)
        seniority = map_seniority(title, text_blob)
        availability_status, availability_reason = self._detect_availability(text_blob)
        if payload.get("availability_status") in {"open", "closed", "unknown"}:
            # Keep explicit browser status, but closed detection from text still wins.
            if availability_status != "closed":
                availability_status = payload["availability_status"]
                availability_reason = payload.get("availability_reason")
        missing = self._missing_fields(title=title, company=company, location_raw=location_raw)
        extraction_status = self._status_for(job_url=job_url, availability_status=availability_status, missing_fields=missing)
        return LinkedInSearchJobCard(
            linkedin_job_id=job_id,
            linkedin_job_url=job_url,
            title=title,
            company=company,
            location_raw=location_raw,
            workplace_type=payload.get("workplace_type") or (workplace.value if workplace else None),
            seniority_hint=payload.get("seniority_hint") or (seniority.value if seniority else None),
            is_easy_apply=payload.get("is_easy_apply"),
            source_search_url=source_search_url or payload.get("source_search_url"),
            collected_at=payload.get("collected_at") or datetime.now(timezone.utc).isoformat(),
            availability_status=availability_status,
            availability_reason=availability_reason,
            extraction_status=extraction_status,
            missing_fields=missing,
            detail_completed=bool(payload.get("detail_completed")) and extraction_status == "complete",
            detail_url_opened=bool(payload.get("detail_url_opened")),
            detail_completion_source=clean_text(payload.get("detail_completion_source")),
            detail_error=clean_text(payload.get("detail_error")),
            card_text_raw=card_text_raw,
            detail_text=detail_text,
            workplace_type_raw=clean_text(payload.get("workplace_type_raw")),
            employment_type_raw=clean_text(payload.get("employment_type_raw")),
        )

    def _extract_title(self, title_link) -> str | None:
        title = None
        if title_link:
            visible_title = title_link.select_one("strong")
            if visible_title is not None:
                title = clean_text(visible_title.get_text(" ", strip=True))
            if not title:
                aria_label = clean_text(title_link.get("aria-label"))
                if aria_label:
                    title = re.sub(r"\s+with verification$", "", aria_label, flags=re.IGNORECASE).strip() or None
            if not title:
                title = clean_text(title_link.get_text(" ", strip=True))
            title = re.sub(r"\s+with verification$", "", title or "", flags=re.IGNORECASE).strip() or None
        return title

    def _normalize_job_url(self, href: str | None, job_id: str) -> str:
        if not href:
            return f"https://www.linkedin.com/jobs/view/{job_id}/"
        if href.startswith("/"):
            href = f"https://www.linkedin.com{href}"
        parsed = urlparse(href)
        host = parsed.netloc or "www.linkedin.com"
        scheme = parsed.scheme or "https"
        return f"{scheme}://{host}/jobs/view/{job_id}/"

    def _job_id_from_href(self, href: str | None) -> str | None:
        if not href:
            return None
        match = re.search(r"/jobs/view/(\d+)", href) or re.search(r"currentJobId=(\d+)", href)
        return match.group(1) if match else None

    def _detect_availability(self, text: str | None) -> tuple[str, str | None]:
        normalized = self._normalize_text(text)
        for marker in CLOSED_MARKERS:
            if self._normalize_text(marker) in normalized:
                return "closed", "expired_or_no_longer_accepting_applications"
        return "unknown", None

    def _normalize_text(self, text: str | None) -> str:
        normalized = (text or "").lower()
        return (
            normalized
            .replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o").replace("õ", "o").replace("ô", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )

    def _missing_fields(self, *, title: str | None, company: str | None, location_raw: str | None) -> list[str]:
        missing = []
        if not title:
            missing.append("title")
        if not company:
            missing.append("company")
        if not location_raw:
            missing.append("location_raw")
        return missing

    def _status_for(self, *, job_url: str | None, availability_status: str, missing_fields: list[str]) -> str:
        if not job_url:
            return "invalid"
        if availability_status == "closed":
            return "closed"
        if missing_fields:
            return "partial"
        return "complete"
