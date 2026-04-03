import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    apply_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    seniority_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seniority_normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_easy_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    availability_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    closed_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    )

    __table_args__ = (
        Index("ix_jobs_canonical_fingerprint", "canonical_url", "fingerprint"),
    )


class RelatedJob(Base):
    __tablename__ = "related_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    related_external_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_related_job_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workplace_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_easy_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    posted_text_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_signal_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    parent_job: Mapped[Job] = relationship(back_populates="related_jobs")

    __table_args__ = (
        Index("ix_related_jobs_parent_job_id", "parent_job_id"),
        Index("ix_related_jobs_related_url", "related_url"),
        Index("ix_related_jobs_canonical_related_job_url", "canonical_related_job_url"),
        Index("ix_related_jobs_parent_url", "parent_job_id", "related_url"),
        UniqueConstraint("parent_job_id", "canonical_related_job_url", name="uq_related_jobs_parent_canonical"),
    )
