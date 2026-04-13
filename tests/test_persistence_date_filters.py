import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Job
from src.schemas.jobs import EnrichmentFilters
from src.services.persistence_service import get_pending_jobs_for_enrichment
from src.core.enums import AvailabilityStatus

@pytest.mark.asyncio
async def test_date_filters_logic_with_real_data(tmp_path):
    # Setup do banco temporário
    db_path = tmp_path / "test_dates.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Inserir dados reais baseados no CSV do usuário
    async with SessionLocal() as session:
        # Vaga coletada ANTES do dia 11 (06/04/2026)
        job_before = Job(
            id="7aa88cdf-73db-4423-b0a5-3f526b0a23c9",
            source="linkedin",
            url="http://link1",
            canonical_url="http://link1",
            title="Analista Desenvolvedor Junior",
            status="success",
            description_text="Descrição aqui",
            availability_status="open",
            fingerprint="fp1",
            parser_used="v1",
            parser_version="v1",
            collected_at=datetime.strptime("2026-04-06 22:45:04", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        )

        # Vaga coletada DEPOIS do dia 11 (12/04/2026)
        job_after = Job(
            id="d446960b-85d7-4db5-ac03-6e27d8db1fc6",
            source="linkedin",
            url="http://link2",
            canonical_url="http://link2",
            title="Desenvolvedor Backend (Python) Jr",
            status="success",
            description_text="Descrição aqui",
            availability_status="open",
            fingerprint="fp2",
            parser_used="v1",
            parser_version="v1",
            collected_at=datetime.strptime("2026-04-12 11:30:23", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        )
        session.add_all([job_before, job_after])
        await session.commit()

    # 2. Testando collected_before (DEVE trazer a vaga do dia 06)
    async with SessionLocal() as session:
        filters_before = EnrichmentFilters(
            collected_before=datetime.strptime("2026-04-11", "%Y-%m-%d").replace(tzinfo=timezone.utc),
            title_includes=["jr"],
            availability_status=AvailabilityStatus.OPEN
        )
        results_before = await get_pending_jobs_for_enrichment(session, limit=10, filters=filters_before)
        
        assert len(results_before) == 1
        assert results_before[0].id == "7aa88cdf-73db-4423-b0a5-3f526b0a23c9"
        assert results_before[0].title == "Analista Desenvolvedor Junior"

    # 3. Testando collected_after (DEVE trazer a vaga do dia 12)
    async with SessionLocal() as session:
        filters_after = EnrichmentFilters(
            collected_after=datetime.strptime("2026-04-11", "%Y-%m-%d").replace(tzinfo=timezone.utc),
            title_includes=["jr"],
            availability_status=AvailabilityStatus.OPEN
        )
        results_after = await get_pending_jobs_for_enrichment(session, limit=10, filters=filters_after)
        
        assert len(results_after) == 1
        assert results_after[0].id == "d446960b-85d7-4db5-ac03-6e27d8db1fc6"
        assert results_after[0].title == "Desenvolvedor Backend (Python) Jr"