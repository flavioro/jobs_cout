import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Job
from src.services.persistence_service import update_job_crm

@pytest.mark.asyncio
async def test_update_job_crm_all_fields_and_preservation(tmp_path):
    # Setup do banco de dados temporário e isolado
    db_path = tmp_path / "test_crm.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Inserir uma vaga "limpa" (antes da candidatura)
    async with SessionLocal() as session:
        job_mock = Job(
            id="vaga-crm-123",
            source="linkedin",
            url="http://linkedin.com/jobs/123",
            canonical_url="http://linkedin.com/jobs/123",
            title="Backend Engineer (AI)",
            status="success",
            description_text="Descrição base",
            fingerprint="fp-crm-1",
            parser_used="v1",
            parser_version="v1",
            collected_at=datetime.now(timezone.utc)
        )
        session.add(job_mock)
        await session.commit()

    # 2. Cenário A: Aplicar para a vaga, adicionar nota e expectativa salarial
    async with SessionLocal() as session:
        updated_job = await update_job_crm(
            session=session,
            job_id="vaga-crm-123",
            applied=True,
            notes="Entrevista com o CTO marcada para terça. Focar em mensageria.",
            salary_expectation="R$ 15.000 PJ"
        )

        assert updated_job is not None
        assert updated_job.applied_at is not None, "A data de candidatura (applied_at) deveria ter sido preenchida."
        assert updated_job.notes == "Entrevista com o CTO marcada para terça. Focar em mensageria."
        assert updated_job.salary_expectation == "R$ 15.000 PJ"

    # 3. Cenário B: Desmarcar a candidatura, mas garantir que as notas e salário são preservados
    async with SessionLocal() as session:
        job_reverted = await update_job_crm(
            session=session,
            job_id="vaga-crm-123",
            applied=False, # Isso deve limpar o applied_at
            # Não passamos notas nem salário, então eles não devem ser alterados
        )

        assert job_reverted.applied_at is None, "A data de candidatura deveria ter sido limpa (None)."
        assert job_reverted.notes == "Entrevista com o CTO marcada para terça. Focar em mensageria.", "As notas não deveriam ser apagadas."
        assert job_reverted.salary_expectation == "R$ 15.000 PJ", "O salário não deveria ser apagado."