from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.core.config import get_settings
from src.core.enums import WorkplaceType
from src.schemas.jobs import IngestUrlRequest


@dataclass
class ImportedCsvJob:
    row_number: int
    source_status: str | None
    linkedin_job_id: str | None
    url: str
    title: str | None
    request: IngestUrlRequest


class CsvImportError(ValueError):
    pass


REQUIRED_COLUMNS = {"linkedin_job_url", "status"}


def resolve_csv_path(csv_path: str | None = None) -> Path:
    settings = get_settings()
    candidate = Path(csv_path or settings.csv_import_default_path)
    if not candidate.exists():
        raise FileNotFoundError(f"CSV não encontrado: {candidate}")
    return candidate



def _normalize_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "sim"}:
        return True
    if normalized in {"false", "0", "no", "não", "nao"}:
        return False
    return None



def _normalize_workplace_type(value: str | None) -> WorkplaceType | None:
    if not value:
        return None
    normalized = value.strip().lower()
    mapping = {
        "remote": WorkplaceType.REMOTE,
        "remoto": WorkplaceType.REMOTE,
        "hybrid": WorkplaceType.HYBRID,
        "hibrido": WorkplaceType.HYBRID,
        "híbrido": WorkplaceType.HYBRID,
        "onsite": WorkplaceType.ONSITE,
        "presencial": WorkplaceType.ONSITE,
        "on-site": WorkplaceType.ONSITE,
    }
    return mapping.get(normalized)



def read_jobs_csv(
    csv_path: str | None = None,
    *,
    status_filter: str | None = None,
    include_all_statuses: bool = False,
    limit: int | None = None,
) -> tuple[Path, list[ImportedCsvJob], int]:
    path = resolve_csv_path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise CsvImportError(f"CSV inválido. Colunas obrigatórias ausentes: {missing_str}")

        rows = list(reader)

    effective_status_filter = None if include_all_statuses else (status_filter or get_settings().csv_import_status_filter)
    selected: list[ImportedCsvJob] = []
    seen_keys: set[str] = set()

    for idx, row in enumerate(rows, start=2):
        row_status = (row.get("status") or "").strip().lower() or None
        if effective_status_filter and row_status != effective_status_filter.strip().lower():
            continue

        url = (row.get("linkedin_job_url") or "").strip()
        if not url:
            continue

        dedupe_key = (row.get("linkedin_job_id") or url).strip()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        request = IngestUrlRequest(
            url=url,
            title=(row.get("title") or "").strip() or None,
            company=(row.get("company") or "").strip() or None,
            location_raw=(row.get("location_raw") or "").strip() or None,
            is_easy_apply=_normalize_bool(row.get("is_easy_apply")),
            seniority_hint=(row.get("seniority") or "").strip() or None,
            workplace_type=_normalize_workplace_type(row.get("work_model")),
        )
        selected.append(
            ImportedCsvJob(
                row_number=idx,
                source_status=row_status,
                linkedin_job_id=(row.get("linkedin_job_id") or "").strip() or None,
                url=url,
                title=(row.get("title") or "").strip() or None,
                request=request,
            )
        )
        if limit is not None and len(selected) >= limit:
            break

    return path, selected, len(rows)
