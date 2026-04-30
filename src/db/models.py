import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    apply_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    seniority_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority_normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)

    sector = Column(String(100), nullable=True)

    is_easy_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    availability_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    closed_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Campos IA / CRM ---
    salary_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills: Mapped[list[str] | dict | None] = mapped_column(JSON, nullable=True)
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    english_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_expectation: Mapped[str | None] = mapped_column(String, nullable=True)

    template_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_used: Mapped[str] = mapped_column(String(100), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    related_jobs: Mapped[list["RelatedJob"]] = relationship(
        back_populates="parent_job",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="RelatedJob.parent_job_id",
    )

    __table_args__ = (
        Index("ix_jobs_canonical_fingerprint", "canonical_url", "fingerprint"),
        Index("ix_jobs_source_external_id", "source", "external_id"),
    )


class RelatedJob(Base):
    __tablename__ = "related_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resolved_job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    related_external_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_related_job_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_easy_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    posted_text_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_signal_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_promoted_to_job: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    promotion_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    promotion_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_promotion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    parent_job: Mapped[Job] = relationship(back_populates="related_jobs", foreign_keys=[parent_job_id])
    resolved_job: Mapped[Job | None] = relationship(foreign_keys=[resolved_job_id])

    __table_args__ = (
        Index("ix_related_jobs_parent_job_id", "parent_job_id"),
        Index("ix_related_jobs_related_url", "related_url"),
        Index("ix_related_jobs_canonical_related_job_url", "canonical_related_job_url"),
        Index("ix_related_jobs_parent_url", "parent_job_id", "related_url"),
        Index("ix_related_jobs_promotion_status_created_at", "promotion_status", "created_at"),
        UniqueConstraint("canonical_related_job_url", name="uq_related_jobs_canonical_global"),
    )


class JobCandidate(Base):
    __tablename__ = "job_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="linkedin", index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_source_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    source_search_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_type_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_easy_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    availability_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    availability_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extraction_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    missing_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    detail_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail_url_opened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail_completion_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_card_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_detail_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    job: Mapped[Job | None] = relationship(foreign_keys=[job_id])

    __table_args__ = (
        Index("ix_job_candidates_source_status", "source", "processing_status"),
        Index("ix_job_candidates_source_collected", "source", "collected_at"),
        UniqueConstraint("source", "source_job_id", name="uq_job_candidates_source_job_id"),
        UniqueConstraint("source", "canonical_source_url", name="uq_job_candidates_source_url"),
    )


class BlockedJob(Base):
    __tablename__ = "blocked_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    block_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("url", name="uq_blocked_jobs_url"),
    )