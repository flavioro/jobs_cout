from datetime import datetime, timezone

from src.core.enums import AvailabilityStatus, ClosedReason, JobSource, JobStatus
from src.core.fingerprint import build_fingerprint
from src.schemas.jobs import IngestUrlRequest, JobRecordSchema, RelatedJobSchema
from src.utils.text import clean_location_raw, map_seniority, map_workplace_type, nullify_placeholder
from src.utils.url import build_canonical_url


def normalize_linkedin_payload(payload, request: IngestUrlRequest) -> JobRecordSchema:
    fields = payload.fields

    title = fields.get("title")
    company = fields.get("company")
    location_raw = clean_location_raw(fields.get("location_raw"))
    description_text = fields.get("description_text")
    is_easy_apply = fields.get("is_easy_apply")
    apply_url = fields.get("apply_url")
    availability_status = AvailabilityStatus(fields.get("availability_status", AvailabilityStatus.UNKNOWN.value))
    closed_reason_value = fields.get("closed_reason")
    closed_reason = ClosedReason(closed_reason_value) if closed_reason_value else None

    workplace_type = map_workplace_type(
        fields.get("workplace_type"),
        request.workplace_type,
        location_raw,
        title,
        description_text,
    )
    seniority_raw = nullify_placeholder(request.seniority_hint)
    seniority_normalized = map_seniority(request.seniority_hint, title, description_text)

    status = JobStatus.SUCCESS
    if not title or not company or not description_text:
        status = JobStatus.PARTIAL

    related_jobs = []
    for item in fields.get("related_jobs", []):
        related_jobs.append(
            RelatedJobSchema.model_validate(
                {
                    **item,
                    "workplace_type": item.get("workplace_type"),
                }
            )
        )

    record = {
        "source": JobSource.LINKEDIN,
        "url": request.url,
        "canonical_url": build_canonical_url(request.url),
        "apply_url": apply_url,
        "title": title,
        "company": company,
        "location_raw": location_raw,
        "workplace_type": workplace_type.value if workplace_type else None,
        "seniority_raw": seniority_raw,
        "seniority_normalized": seniority_normalized.value if seniority_normalized else None,
        "is_easy_apply": is_easy_apply,
        "availability_status": availability_status.value,
        "closed_reason": closed_reason.value if closed_reason else None,
        "description_text": description_text,
        "template_source": "linkedin_default",
        "parser_used": "linkedin_css_bs4",
        "parser_version": "linkedin_v1.1",
        "status": status.value,
        "collected_at": datetime.now(timezone.utc),
        "fingerprint": "",
        "raw_html_path": None,
        "related_jobs": related_jobs,
    }
    record["fingerprint"] = build_fingerprint(record)
    return JobRecordSchema.model_validate(record)
