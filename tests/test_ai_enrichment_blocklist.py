import pytest
from unittest.mock import AsyncMock, patch
from src.services.ai_enrichment_service import enrich_pending_jobs

@pytest.mark.asyncio
async def test_enrich_pending_jobs_blocks_and_deletes_forbidden_titles(monkeypatch):
    mock_session = AsyncMock()
    
    # Simulamos uma vaga que contém "marketing" no título
    mock_job = AsyncMock()
    mock_job.id = "ghost-job-123"
    mock_job.title = "Gerente de Marketing Digital"
    mock_job.source = "linkedin"
    mock_job.url = "http://link.com"
    
    # Mock das configurações (Agora com o user_profile_context)
    class MockSettings:
        parsed_title_blocklist = ["marketing"]
        groq_api_key = "fake-key"
        groq_model = "llama-3.3"
        user_profile_context = "Perfil Mock"

    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())
    
    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
        with patch("src.services.ai_enrichment_service.save_blocked_job", new_callable=AsyncMock) as mock_save_block:
            with patch("src.services.ai_enrichment_service.delete_job", new_callable=AsyncMock) as mock_delete:
                
                result = await enrich_pending_jobs(mock_session, limit=1)
                
                # Verificações
                assert result["blocked"] == 1
                mock_save_block.assert_called_once()
                mock_delete.assert_called_once_with(mock_session, "ghost-job-123")
                assert "processed" not in result or result["processed"] == 0