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
    EnglishLevel,
)
from src.utils.url import is_supported_linkedin_url


from src.core.enums import EnglishLevel, AvailabilityStatus, SeniorityLevel, WorkplaceType

class JobCRMUpdate(BaseModel):
    applied: bool | None = Field(None, description="Se True, marca a data de hoje em applied_at. Se False, limpa o campo.")
    notes: str | None = Field(None, description="Suas notas pessoais sobre a vaga (entrevistas, feedback, etc.)")
    salary_expectation: str | None = Field(None, description="O valor da pretensão salarial informada na candidatura.")

class EnrichmentFilters(BaseModel):
    english_level: EnglishLevel | None = None
    fit_score_min: int | None = None
    fit_score_max: int | None = None
    availability_status: AvailabilityStatus | None = None
    is_easy_apply: bool | None = None
    seniority_normalized: SeniorityLevel | None = None
    workplace_type: WorkplaceType | None = None
    collected_after: datetime | None = None
    collected_before: datetime | None = None
    title_includes: list[str] | None = None
    seniority_null: bool | None = None
    workplace_null: bool | None = None
    english_null: bool | None = None
    description_null: bool | None = None

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
    source: JobSource
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
    availability_status: AvailabilityStatus | None = None
    closed_reason: ClosedReason | None = None
    description_text: str | None = None
    template_source: str | None = None
    parser_used: str
    parser_version: str
    status: JobStatus
    fingerprint: str
    raw_html_path: str | None = None
    collected_at: datetime
    
    # --- Novos Campos Opcionais (IA e CRM) ---
    salary_raw: str | None = None
    skills: list[str] | dict | None = None
    fit_score: int | None = None
    fit_rationale: str | None = None
    english_level: EnglishLevel | None = None
    applied_at: datetime | None = None
    notes: str | None = None
    
    related_jobs: list[RelatedJobSchema] = Field(default_factory=list)


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
    job_id: str | None = None
    parser_version: str | None = None
    confirmation: ConfirmationPayload | None = None
    job: dict | None = None
    block_reason: str | None = None


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
    
    # --- Novos Campos Opcionais (IA e CRM) ---
    salary_raw: str | None = None
    skills: list[str] | dict | None = None
    fit_score: int | None = None
    fit_rationale: str | None = None
    english_level: str | None = None
    applied_at: datetime | None = None
    salary_expectation: str | None
    notes: str | None = None

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
    total: int
    items: list[RelatedJobRead]


class LinkedinPromotePendingRelatedJobsRequest(BaseModel):
    limit: int = Field(10, ge=1, le=100)


class LinkedinPromotePendingRelatedJobsResponse(BaseModel):
    requested_limit: int
    processed: int
    promoted: int
    already_resolved: int
    failed: int
    skipped: int
    items: list[dict]