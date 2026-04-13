import pytest
from unittest.mock import AsyncMock, patch
from src.schemas.jobs import EnrichmentFilters
from src.services.ai_enrichment_service import enrich_pending_jobs
from src.core.enums import WorkplaceType, SeniorityLevel

@pytest.mark.asyncio
async def test_enrich_pending_jobs_passes_filters_to_repository(monkeypatch):
    mock_session = AsyncMock()
    
    # 1. Criamos um filtro simulando o input do usuário na API
    filters = EnrichmentFilters(
        workplace_type=WorkplaceType.REMOTE,
        seniority_normalized=SeniorityLevel.MID,
        is_easy_apply=True
    )

    # 2. Mock das configurações para não pedir API Key real
    class MockSettings:
        groq_api_key = "fake-key"
    
    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    # 3. Interceptamos a chamada ao banco de dados
    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[]) as mock_repo:
        
        # 4. Executamos o serviço
        await enrich_pending_jobs(mock_session, limit=5, filters=filters)

        # 5. Verificamos se o serviço repassou os filtros perfeitamente para o repositório
        mock_repo.assert_called_once_with(mock_session, limit=5, filters=filters)

@pytest.mark.asyncio
async def test_enrich_pending_jobs_handles_empty_filters_correctly(monkeypatch):
    mock_session = AsyncMock()
    
    class MockSettings:
        groq_api_key = "fake-key"
    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    # Testando com filters=None (Comportamento padrão)
    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[]) as mock_repo:
        await enrich_pending_jobs(mock_session, limit=10, filters=None)
        mock_repo.assert_called_once_with(mock_session, limit=10, filters=None)