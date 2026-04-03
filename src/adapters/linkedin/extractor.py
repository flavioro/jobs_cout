from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from src.adapters.linkedin.selectors import LINKEDIN_SELECTORS
from src.core.contracts import RawJobPayload, RawPage
from src.utils.text import (
    clean_location_raw,
    clean_text,
    detect_availability,
    extract_workplace_type_from_text,
    sanitize_title,
)
from src.utils.url import build_canonical_related_job_url


def parse_from_page_title(page_title: str | None) -> tuple[str | None, str | None]:
    if not page_title:
        return None, None

    parts = [p.strip() for p in page_title.split("|") if p.strip()]
    if len(parts) >= 3 and parts[-1].lower() == "linkedin":
        title = parts[0]
        company = parts[-2]
        return title, company
    return None, None


class LinkedInExtractor:
    source_name = "linkedin"

    def extract(self, raw_page: RawPage) -> RawJobPayload:
        soup = BeautifulSoup(raw_page.html, "lxml")
        notes: list[str] = []

        def find_first_text(selectors: list[str]) -> str | None:
            for selector in selectors:
                node = soup.select_one(selector)
                if node:
                    text = clean_text(node.get_text(" ", strip=True))
                    if text:
                        return text
            return None

        title = find_first_text(LINKEDIN_SELECTORS["title"])
        company = find_first_text(LINKEDIN_SELECTORS["company"])
        description_text = find_first_text(LINKEDIN_SELECTORS["description"])

        title_from_tab, company_from_tab = parse_from_page_title(raw_page.title)
        raw_title_candidate = title or title_from_tab
        company = company or company_from_tab
        title = sanitize_title(raw_title_candidate, company)

        location_raw = self._extract_location(soup)
        body_text = clean_text(soup.get_text(" ", strip=True))
        main_region = soup.select_one("main") or soup
        primary_text = clean_text(main_region.get_text(" ", strip=True)) or ""
        primary_text_lower = primary_text.lower()
        if "mais vagas" in primary_text_lower:
            primary_text = primary_text[: primary_text_lower.index("mais vagas")].strip()
        availability_status, closed_reason = detect_availability(body_text)
        workplace_type = extract_workplace_type_from_text(location_raw, raw_title_candidate, raw_page.title, description_text, primary_text)
        is_easy_apply = self._detect_easy_apply(soup, availability_status.value)
        related_jobs = self._extract_related_jobs(soup)

        if not title:
            notes.append("title_not_found")
        if not company:
            notes.append("company_not_found")
        if not description_text:
            notes.append("description_not_found")
        if not location_raw:
            notes.append("location_not_found")
        if availability_status.value == "closed":
            notes.append("job_closed")

        return RawJobPayload(
            source="linkedin",
            source_url=raw_page.final_url or raw_page.url,
            fields={
                "title": title,
                "company": company,
                "location_raw": location_raw,
                "description_text": description_text,
                "is_easy_apply": is_easy_apply,
                "apply_url": raw_page.apply_url,
                "workplace_type": workplace_type.value if workplace_type else None,
                "availability_status": availability_status.value,
                "closed_reason": closed_reason.value if closed_reason else None,
                "related_jobs": related_jobs,
            },
            extraction_notes=notes,
        )

    def _extract_location(self, soup: BeautifulSoup) -> str | None:
        location_raw = None
        for selector in LINKEDIN_SELECTORS["location"]:
            node = soup.select_one(selector)
            if node:
                text = clean_text(node.get_text(" ", strip=True))
                cleaned = clean_location_raw(text)
                if cleaned:
                    location_raw = cleaned
                    break

        if not location_raw:
            for p in soup.find_all("p"):
                text = clean_text(p.get_text(" ", strip=True))
                if not text:
                    continue
                if "· há " in text or "· há" in text or "compartilhou há" in text.lower():
                    possible_location = clean_location_raw(text)
                    if possible_location and len(possible_location) <= 120:
                        location_raw = possible_location
                        break
        return location_raw

    def _detect_easy_apply(self, soup: BeautifulSoup, availability_status: str) -> bool:
        if availability_status == "closed":
            return False

        main_region = soup.select_one("main") or soup
        body_text = clean_text(main_region.get_text(" ", strip=True)) or ""
        body_text_lower = body_text.lower()
        if "mais vagas" in body_text_lower:
            body_text_lower = body_text_lower.split("mais vagas", 1)[0]

        top_signals = [
            "candidatura simplificada",
            "easy apply",
        ]
        return any(term in body_text_lower for term in top_signals)

    def _extract_related_jobs(self, soup: BeautifulSoup) -> list[dict]:
        related: list[dict] = []
        seen_canonical: set[str] = set()
        anchors = soup.select("a[href*='currentJobId=']")
        for anchor in anchors:
            href = anchor.get("href")
            if not href:
                continue
            parsed = self._parse_related_job_anchor(anchor, href)
            if not parsed:
                continue
            canonical_url = parsed.get("canonical_related_job_url")
            dedupe_key = canonical_url or parsed["related_url"]
            if dedupe_key in seen_canonical:
                continue
            seen_canonical.add(dedupe_key)
            related.append(parsed)
        return related

    def _looks_like_location(self, value: str | None) -> bool:
        if not value:
            return False
        lowered = value.lower()
        location_signals = [
            "(remoto)", "(híbrido)", "(hibrido)", "(presencial)",
            " remoto", " híbrido", " hibrido", " presencial",
            "remote", "hybrid", "onsite",
            "são paulo", "brasil", ", sp", ", rj", ", mg", ", pr", ", sc", ", rs",
        ]
        return any(signal in lowered for signal in location_signals)

    def _looks_like_company_name(self, value: str | None) -> bool:
        if not value:
            return False
        lowered = value.lower()
        company_signals = [
            "ltda", "s.a", "inc", "llc", "solutions", "technology", "technologies",
            "digital", "software", "investimentos", "consulting", "corp", "group",
        ]
        return any(signal in lowered for signal in company_signals)

    def _sanitize_related_company_and_location(self, title: str | None, candidate_lines: list[str]) -> tuple[str | None, str | None]:
        normalized_title = clean_text(title)
        usable_lines: list[str] = []
        for line in candidate_lines:
            cleaned = clean_text(line)
            if not cleaned:
                continue
            usable_lines.append(cleaned)

        company = None
        location_raw = None

        for cleaned in usable_lines:
            if location_raw is None and self._looks_like_location(cleaned):
                location_raw = clean_location_raw(cleaned)
                continue
            if company is None:
                company = cleaned
                continue
            if location_raw is None:
                location_raw = clean_location_raw(cleaned)

        title_variants: set[str] = set()
        if normalized_title:
            title_variants.add(normalized_title.casefold())
            sanitized_title = sanitize_title(normalized_title)
            if sanitized_title:
                title_variants.add(sanitized_title.casefold())
            verified_stripped_title = clean_text(normalized_title.replace("(Vaga verificada)", "").replace("(vaga verificada)", ""))
            if verified_stripped_title:
                title_variants.add(verified_stripped_title.casefold())

        if company and title_variants and company.casefold() in title_variants:
            company = None
            for cleaned in usable_lines:
                candidate_sanitized = sanitize_title(cleaned)
                if cleaned.casefold() in title_variants:
                    continue
                if candidate_sanitized and candidate_sanitized.casefold() in title_variants:
                    continue
                if self._looks_like_location(cleaned):
                    if location_raw is None:
                        location_raw = clean_location_raw(cleaned)
                    continue
                company = cleaned
                break

        if company and location_raw:
            company_looks_like_location = self._looks_like_location(company)
            location_looks_like_location = self._looks_like_location(location_raw)
            location_looks_like_company = self._looks_like_company_name(location_raw)
            if company_looks_like_location and (not location_looks_like_location or location_looks_like_company):
                company, location_raw = location_raw, company

        if company and title_variants and company.casefold() in title_variants:
            company = None
            for cleaned in usable_lines:
                candidate_sanitized = sanitize_title(cleaned)
                if cleaned.casefold() in title_variants:
                    continue
                if candidate_sanitized and candidate_sanitized.casefold() in title_variants:
                    continue
                if cleaned == location_raw:
                    continue
                if self._looks_like_location(cleaned):
                    if location_raw is None:
                        location_raw = clean_location_raw(cleaned)
                    continue
                company = cleaned
                break

        if company and location_raw and company.casefold() == location_raw.casefold():
            location_raw = None

        return company, clean_location_raw(location_raw)

    def _parse_related_job_anchor(self, anchor: Tag, href: str) -> dict | None:
        lines = [clean_text(line) for line in anchor.stripped_strings]
        lines = [line for line in lines if line and line != "·"]
        if len(lines) < 3:
            return None

        title = lines[0]
        is_verified = "vaga verificada" in title.lower()
        remaining = lines[1:]

        if is_verified and remaining:
            first_remaining_sanitized = sanitize_title(remaining[0])
            title_sanitized = sanitize_title(title)
            if first_remaining_sanitized and title_sanitized and first_remaining_sanitized.casefold() == title_sanitized.casefold():
                remaining = remaining[1:]

        metadata_lines: list[str] = []
        posted_text_raw = None
        candidate_signal_raw = None
        is_easy_apply = False

        for line in remaining:
            lowered = line.lower()
            if lowered == "candidatura simplificada":
                is_easy_apply = True
                continue
            if "avaliando candidatura" in lowered:
                candidate_signal_raw = line
                continue
            if lowered.startswith("anunciada há"):
                posted_text_raw = line
                continue
            if lowered.startswith("há ") and posted_text_raw is None:
                posted_text_raw = line
                continue
            metadata_lines.append(line)

        company, location_raw = self._sanitize_related_company_and_location(title, metadata_lines)
        workplace_type_enum = extract_workplace_type_from_text(location_raw, title)
        workplace_type = workplace_type_enum.value if workplace_type_enum else None

        current_job_id = parse_qs(urlparse(href).query).get("currentJobId", [None])[0]
        canonical_related_job_url = build_canonical_related_job_url(current_job_id, href)

        sanitized_title = sanitize_title(title, company)
        if company and sanitized_title and company.casefold() == sanitized_title.casefold():
            company = None

        return {
            "related_external_id": current_job_id,
            "related_url": href,
            "canonical_related_job_url": canonical_related_job_url,
            "title": sanitized_title,
            "company": company,
            "location_raw": clean_location_raw(location_raw),
            "workplace_type": workplace_type,
            "is_easy_apply": is_easy_apply,
            "posted_text_raw": posted_text_raw,
            "candidate_signal_raw": candidate_signal_raw,
            "is_verified": is_verified,
        }
