from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import require_api_key
from src.db.models import Job, RelatedJob
from src.db.session import get_db_session
from src.schemas.jobs import HealthResponse, IngestUrlRequest, IngestUrlResponse, JobRead, RelatedJobListRead, RelatedJobRead
from src.services.ingest_service import ingest_url
from src.services.persistence_service import list_related_jobs

router = APIRouter(tags=["jobs"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/ingest-url", response_model=IngestUrlResponse, dependencies=[Depends(require_api_key)])
async def ingest_url_endpoint(
    request: IngestUrlRequest,
    session: AsyncSession = Depends(get_db_session),
) -> IngestUrlResponse:
    return await ingest_url(request=request, session=session)


@router.get("/jobs/{job_id}", response_model=JobRead, dependencies=[Depends(require_api_key)])
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)




@router.get("/related-jobs", response_model=RelatedJobListRead, dependencies=[Depends(require_api_key)])
async def get_all_related_jobs(
    parent_job_id: str | None = Query(default=None),
    company: str | None = Query(default=None),
    workplace_type: str | None = Query(default=None),
    is_easy_apply: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> RelatedJobListRead:
    return await list_related_jobs(
        session=session,
        parent_job_id=parent_job_id,
        company=company,
        workplace_type=workplace_type,
        is_easy_apply=is_easy_apply,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}/related", response_model=list[RelatedJobRead], dependencies=[Depends(require_api_key)])
async def get_related_jobs(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[RelatedJobRead]:
    result = await session.execute(select(RelatedJob).where(RelatedJob.parent_job_id == job_id).order_by(RelatedJob.created_at.desc()))
    items = result.scalars().all()
    return [RelatedJobRead.model_validate(item) for item in items]


@router.get("/jobs", response_model=list[JobRead], dependencies=[Depends(require_api_key)])
async def list_jobs(session: AsyncSession = Depends(get_db_session)) -> list[JobRead]:
    result = await session.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return [JobRead.model_validate(job) for job in jobs]
