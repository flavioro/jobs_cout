import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Job, BlockedJob
from src.schemas.jobs import IngestUrlRequest, IngestUrlResponse
from src.core.contracts import RawPage, RawJobPayload
from src.services.ingest_service import ingest_linkedin_request


@pytest.mark.asyncio
async def test_ingest_linkedin_request_blocks_job_and_saves_to_blocked_table(tmp_path, monkeypatch):
    # Setup de um banco de dados em memória/arquivo temporário
    db_path = tmp_path / "ingest_blocked.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Mock do Settings para forçar uma blocklist
    class MockSettings:
        parsed_title_blocklist = ["marketing", "vendas"]
        raw_html_dir = str(tmp_path)
    
    monkeypatch.setattr("src.services.ingest_service.get_settings", MockSettings)

    # 2. Mock do Adapter para não precisar fazer requests reais (Playwright) durante o teste
    class MockAdapter:
        async def fetch(self, url):
            return RawPage(url=url, final_url=url, html="<html></html>", title="Analista de Marketing")
            
        def extract(self, raw_page):
            return RawJobPayload(source="linkedin", source_url=raw_page.url, fields={}, extraction_notes=[])
            
        def normalize(self, payload, request):
            from src.schemas.jobs import JobRecordSchema
            from src.core.enums import JobSource, JobStatus, AvailabilityStatus
            from datetime import datetime, timezone
            
            return JobRecordSchema(
                source=JobSource.LINKEDIN,
                url=request.url,
                canonical_url=request.url,
                title="Analista de Marketing Pleno", # A palavra proibida!
                company="Empresa Ruim",
                parser_used="mock",
                parser_version="1.0",
                status=JobStatus.SUCCESS,
                availability_status=AvailabilityStatus.OPEN,
                fingerprint="123",
                collected_at=datetime.now(timezone.utc),
                related_jobs=[]
            )

    class MockAdapterFactory:
        @staticmethod
        def get_adapter(url):
            return MockAdapter()

    monkeypatch.setattr("src.services.ingest_service.AdapterFactory", MockAdapterFactory)

    # 3. Executar o serviço
    request = IngestUrlRequest(url="https://www.linkedin.com/jobs/view/999/")
    async with SessionLocal() as session:
        response: IngestUrlResponse = await ingest_linkedin_request(request, session)

        # Verificações
        assert response.status == "blocked"
        assert response.job_id is None
        assert "marketing" in response.block_reason

        # Verificar se não guardou no `jobs`
        jobs_count = (await session.execute(select(Job))).scalars().all()
        assert len(jobs_count) == 0

        # Verificar se guardou no `blocked_jobs`
        blocked_jobs = (await session.execute(select(BlockedJob))).scalars().all()
        assert len(blocked_jobs) == 1
        assert blocked_jobs[0].title == "Analista de Marketing Pleno"
        assert blocked_jobs[0].company == "Empresa Ruim"