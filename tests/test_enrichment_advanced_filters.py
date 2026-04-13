# tests/test_enrichment_advanced_filters.py
import pytest
from unittest.mock import AsyncMock, patch
from src.schemas.jobs import EnrichmentFilters
from src.services.ai_enrichment_service import enrich_pending_jobs

@pytest.mark.asyncio
async def test_enrichment_filters_title_keywords_logic(monkeypatch):
    mock_session = AsyncMock()
    
    # 1. Filtro com múltiplas palavras e check de nulo
    filters = EnrichmentFilters(
        title_includes=["python", "pleno"],
        seniority_null=True
    )

    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment") as mock_repo:
        mock_repo.return_value = []
        
        await enrich_pending_jobs(mock_session, filters=filters)
        
        # 2. Validamos se o objeto filters chegou ao repositório corretamente
        args, kwargs = mock_repo.call_args
        sent_filters = kwargs['filters']
        
        assert "python" in sent_filters.title_includes
        assert "pleno" in sent_filters.title_includes
        assert sent_filters.seniority_null is True