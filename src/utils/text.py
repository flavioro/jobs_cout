import re
import unicodedata
from typing import Iterable

from src.core.enums import AvailabilityStatus, ClosedReason, SeniorityLevel, WorkplaceType


PLACEHOLDER_NULLS = {"", "string", "none", "null", "undefined", "n/a", "na"}


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def nullify_placeholder(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    if cleaned.lower() in PLACEHOLDER_NULLS:
        return None
    return cleaned


def normalize_for_compare(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[\s\-_]+", " ", normalized)
    return normalized


def clean_location_raw(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if not cleaned:
        return None

    noisy_patterns = [
        r"\s*·\s*há\s+.+$",
        r"\s*·\s*mais de\s+\d+\s+(?:pessoas\s+clicaram em candidate-se|candidaturas).*$",
        r"\s*·\s*\d+\s+pessoas\s+clicaram em candidate-se.*$",
        r"\s*·\s*compartilhou\s+há\s+.+$",
        r"\s*·\s*avaliando candidaturas.*$",
    ]
    for pattern in noisy_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s*·\s*$", "", cleaned).strip()
    return cleaned or None


def extract_workplace_type_from_text(*values: str | None) -> WorkplaceType | None:
    combined = " ".join(v for v in values if v)
    normalized = normalize_for_compare(combined)
    if not normalized:
        return None
    if any(term in normalized for term in ["100% remoto", "100 remoto", "remoto", "remote", "trabalho remoto"]):
        return WorkplaceType.REMOTE
    if any(term in normalized for term in ["hibrido", "hybrid"]):
        return WorkplaceType.HYBRID
    if any(term in normalized for term in ["presencial", "onsite", "on site"]):
        return WorkplaceType.ONSITE
    return None


def map_workplace_type(*values: str | WorkplaceType | None) -> WorkplaceType | None:
    for value in values:
        if isinstance(value, WorkplaceType):
            return value
    text_values = [str(v) for v in values if isinstance(v, str)]
    return extract_workplace_type_from_text(*text_values)


def map_seniority(*values: str | None) -> SeniorityLevel | None:
    text = " ".join(v for v in values if v)
    normalized = normalize_for_compare(text)
    if not normalized:
        return None

    def has_term(patterns: list[str]) -> bool:
        return any(re.search(pattern, normalized) for pattern in patterns)

    if has_term([r"\bestagio\b", r"\bintern\b", r"\btrainee\b"]):
        return SeniorityLevel.INTERN
    if has_term([r"\bjunior\b", r"\bjr\b"]):
        return SeniorityLevel.JUNIOR
    if has_term([r"\bpleno\b", r"\bmid\b", r"\bmiddle\b"]):
        return SeniorityLevel.MID
    if has_term([r"\bsenior\b", r"\bsr\b"]):
        return SeniorityLevel.SENIOR
    if has_term([r"\blead\b", r"\blider\b", r"\bprincipal\b"]):
        return SeniorityLevel.LEAD
    if has_term([r"\bmanager\b", r"\bgerente\b"]):
        return SeniorityLevel.MANAGER
    return None


def detect_availability(body_text: str | None) -> tuple[AvailabilityStatus, ClosedReason | None]:
    normalized = normalize_for_compare(body_text or "")
    if not normalized:
        return AvailabilityStatus.UNKNOWN, None
    if "nao aceita mais candidaturas" in normalized or "não aceita mais candidaturas" in (body_text or "").lower():
        return AvailabilityStatus.CLOSED, ClosedReason.DOES_NOT_ACCEPT_APPLICATIONS
    if "vaga removida" in normalized or "job is no longer available" in normalized:
        return AvailabilityStatus.CLOSED, ClosedReason.REMOVED
    return AvailabilityStatus.OPEN, None


def sanitize_title(title: str | None, company: str | None = None) -> str | None:
    cleaned = clean_text(title)
    if not cleaned:
        return None

    cleaned = re.sub(r"\s*\|\s*LinkedIn\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\((Remoto|Remote|Híbrido|Hibrido|Presencial|Onsite)\)\s*$", "", cleaned, flags=re.IGNORECASE)

    if company:
        company_norm = re.escape(company.strip())
        cleaned = re.sub(rf"\s*\|\s*{company_norm}\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf"\s*-\s*{company_norm}\s*$", "", cleaned, flags=re.IGNORECASE)

    return clean_text(cleaned)
