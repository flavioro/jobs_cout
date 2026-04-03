from dataclasses import dataclass
from typing import Any


@dataclass
class RawPage:
    url: str
    final_url: str
    html: str
    title: str | None
    screenshot_path: str | None = None
    storage_state_used: bool = False
    apply_url: str | None = None


@dataclass
class RawJobPayload:
    source: str
    source_url: str
    fields: dict[str, Any]
    extraction_notes: list[str]


@dataclass
class SavedJob:
    internal_id: str
    status: str
    fingerprint: str
