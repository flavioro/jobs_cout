from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from src.core.enums import (
    AvailabilityStatus,
    ClosedReason,
    ConfirmationStatus,
    JobSource,
    JobStatus,
    SeniorityLevel,
    WorkplaceType,
)
from src.utils.url import is_supported_linkedin_url


class HealthResponse(BaseModel):
    status: Literal["ok"]


class IngestUrlRequest(BaseModel):
    url: str = Field(..., description="URL da vaga do LinkedIn")
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    is_easy_apply: bool | None = None
    seniority_hint: str | None = None
    workplace_type: WorkplaceType | None = Field(
        default=None,
        validation_alias=AliasChoices("workplace_type", "work_model"),
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not is_supported_linkedin_url(value):
            raise ValueError("URL must be a supported LinkedIn job URL")
        return value


class RelatedJobSchema(BaseModel):
    related_external_id: str | None = None
    related_url: str
    canonical_related_job_url: str | None = None
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    workplace_type: WorkplaceType | None = None
    is_easy_apply: bool | None = None
    posted_text_raw: str | None = None
    candidate_signal_raw: str | None = None
    is_verified: bool = False


class JobRecordSchema(BaseModel):
    source: JobSource = Field(default=JobSource.LINKEDIN)
    external_id: str | None = None
    url: str
    canonical_url: str
    apply_url: str | None = None
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    workplace_type: WorkplaceType | None = None
    seniority_raw: str | None = None
    seniority_normalized: SeniorityLevel | None = None
    is_easy_apply: bool | None = None
    availability_status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    closed_reason: ClosedReason | None = None
    description_text: str | None = None
    template_source: str | None = None
    parser_used: str
    parser_version: str
    status: JobStatus
    collected_at: datetime
    fingerprint: str
    raw_html_path: str | None = None
    related_jobs: list[RelatedJobSchema] = []


class ConfirmationPayload(BaseModel):
    title: ConfirmationStatus
    company: ConfirmationStatus
    location_raw: ConfirmationStatus
    is_easy_apply: ConfirmationStatus
    seniority_hint: ConfirmationStatus
    workplace_type: ConfirmationStatus


class IngestUrlResponse(BaseModel):
    status: str
    source: str
    job_id: str
    parser_version: str
    confirmation: ConfirmationPayload
    job: dict


class LinkedinPromotePendingRelatedJobsRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)


class LinkedinPromotePendingRelatedJobsResponse(BaseModel):
    source: Literal["linkedin"] = "linkedin"
    requested_limit: int
    processed: int
    promoted: int
    already_resolved: int
    failed: int
    skipped: int
    items: list[dict]


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    external_id: str | None = None
    url: str
    canonical_url: str
    apply_url: str | None = None
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    workplace_type: str | None = None
    seniority_raw: str | None = None
    seniority_normalized: str | None = None
    is_easy_apply: bool | None = None
    availability_status: str | None = None
    closed_reason: str | None = None
    description_text: str | None = None
    template_source: str | None = None
    parser_used: str
    parser_version: str
    status: str
    fingerprint: str
    raw_html_path: str | None = None
    created_at: datetime
    updated_at: datetime
    collected_at: datetime


class RelatedJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parent_job_id: str
    resolved_job_id: str | None = None
    related_external_id: str | None = None
    related_url: str
    canonical_related_job_url: str | None = None
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    workplace_type: str | None = None
    is_easy_apply: bool | None = None
    posted_text_raw: str | None = None
    candidate_signal_raw: str | None = None
    is_verified: bool
    is_promoted_to_job: bool
    promotion_status: str
    promotion_attempts: int
    last_promotion_error: str | None = None
    last_promoted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RelatedJobListRead(BaseModel):
    items: list[RelatedJobRead]
    total: int
    limit: int
    offset: int
