from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_api_key
from src.db.models import Job, RelatedJob
from src.db.session import get_db_session
from datetime import datetime
from src.schemas.jobs import EnrichmentFilters
from src.core.enums import EnglishLevel, AvailabilityStatus, SeniorityLevel, WorkplaceType
from src.schemas.jobs import (
    HealthResponse,
    IngestUrlRequest,
    IngestUrlResponse,
    JobRead,
    LinkedinPromotePendingRelatedJobsRequest,
    LinkedinPromotePendingRelatedJobsResponse,
    RelatedJobListRead,
    RelatedJobRead,
)
from src.services.ingest_service import ingest_url
from src.services.linkedin_related_job_promotion_service import promote_pending_linkedin_related_jobs
from src.services.persistence_service import list_related_jobs

# --- Nova importação da IA ---
from src.services.ai_enrichment_service import enrich_pending_jobs

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


@router.post(
    "/linkedin/related-jobs/promote-pending",
    response_model=LinkedinPromotePendingRelatedJobsResponse,
    dependencies=[Depends(require_api_key)],
)
async def promote_pending_linkedin_related_jobs_endpoint(
    request: LinkedinPromotePendingRelatedJobsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LinkedinPromotePendingRelatedJobsResponse:
    return await promote_pending_linkedin_related_jobs(session=session, limit=request.limit)


@router.get("/related-jobs", response_model=RelatedJobListRead, dependencies=[Depends(require_api_key)])
async def get_all_related_jobs(
    parent_job_id: str | None = Query(default=None),
    company: str | None = Query(default=None),
    workplace_type: str | None = Query(default=None),
    is_easy_apply: bool | None = Query(default=None),
    promotion_status: str | None = Query(default=None),
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
        promotion_status=promotion_status,
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
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[JobRead]:
    result = await session.execute(select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset))
    items = result.scalars().all()
    return [JobRead.model_validate(item) for item in items]


@router.get("/jobs/{job_id}", response_model=JobRead, dependencies=[Depends(require_api_key)])
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    job = await session.scalar(select(Job).where(Job.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)


# --- Novo Endpoint para Enriquecimento com IA ---
@router.post(
    "/linkedin/jobs/enrich",
    summary="Enriquece vagas usando filtros e Groq LLM",
    description="Filtre vagas específicas antes de enviar para a IA.",
    dependencies=[Depends(require_api_key)],
)
async def enrich_jobs_with_ai(
    limit: int = Query(10, ge=1, le=50, description="Máximo de vagas"),
    english_level: EnglishLevel | None = Query(None, description="Filtrar por nível de inglês"),
    fit_score_min: int | None = Query(None, ge=0, le=100, description="Score mínimo (para reprocessamento)"),
    fit_score_max: int | None = Query(None, ge=0, le=100, description="Score máximo"),
    availability_status: AvailabilityStatus | None = Query(None, description="Status da vaga (ex: open)"),
    is_easy_apply: bool | None = Query(None, description="Apenas vagas de candidatura simplificada?"),
    seniority_normalized: SeniorityLevel | None = Query(None, description="Nível de senioridade"),
    workplace_type: WorkplaceType | None = Query(None, description="Ex: remote, hybrid"),
    collected_after: datetime | None = Query(None, description="Coletadas após (ISO 8601)"),
    collected_before: datetime | None = Query(None, description="Coletadas antes (ISO 8601)"),
    title_includes: str | None = Query(None, description="Palavras obrigatórias no título (ex: jr, backend)"),
    seniority_null: bool | None = Query(None, description="Buscar apenas onde senioridade está vazia?"),
    workplace_null: bool | None = Query(None, description="Buscar apenas onde workplace_type está vazio?"),
    english_null: bool | None = Query(None, description="Buscar apenas onde o ingles está vazio?"),
    description_null: bool | None = Query(None, description="Buscar apenas onde a descrição está vazia?"),
    db_session: AsyncSession = Depends(get_db_session)
):
    # Transforma "jr, backend" em ["jr", "backend"] limpando os espaços
    parsed_title_includes = [word.strip() for word in title_includes.split(",")] if title_includes else None

    filters = EnrichmentFilters(
        english_level=english_level,
        fit_score_min=fit_score_min,
        fit_score_max=fit_score_max,
        availability_status=availability_status,
        is_easy_apply=is_easy_apply,
        seniority_normalized=seniority_normalized,
        workplace_type=workplace_type,
        collected_after=collected_after,
        collected_before=collected_before,
        title_includes=parsed_title_includes,
        seniority_null=seniority_null,
        workplace_null=workplace_null,
        english_null=english_null,
        description_null=description_null
    )
    
    result = await enrich_pending_jobs(session=db_session, limit=limit, filters=filters)
    return result