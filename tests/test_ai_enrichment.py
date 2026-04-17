import pytest
from unittest.mock import AsyncMock, patch
from src.services.ai_enrichment_service import enrich_pending_jobs
from src.core.enums import EnglishLevel

@pytest.mark.asyncio
async def test_enrich_pending_jobs_updates_db_correctly(tmp_path, monkeypatch):
    # Isolamos as configurações do ambiente real
    class MockSettings:
        parsed_title_blocklist = []
        groq_api_key = "fake-key"
        groq_model = "llama-3.3"
        user_profile_context = "Perfil Mock"

    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    # 1. Mock do retorno da Groq (JSON esperado)
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="""
        {
            "skills": ["Python", "FastAPI"],
            "fit_score": 90,
            "fit_rationale": "Você tem as skills necessárias.",
            "seniority_suggestion": "junior",
            "english_level": "advanced"
        }
        """))
    ]

    # 2. Injetamos o Mock no cliente da Groq
    with patch("src.services.ai_enrichment_service.AsyncGroq") as mock_groq:
        mock_groq.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Simulamos uma sessão de banco e uma vaga pendente limpa
        mock_session = AsyncMock()
        mock_job = AsyncMock()
        mock_job.id = "test-id"
        mock_job.title = "Python Developer"
        mock_job.source = "linkedin"
        mock_job.url = "http://link.com"
        mock_job.company = "Tech Corp"
        mock_job.description_text = "Vaga para Python e FastAPI"
        mock_job.seniority_normalized = None
        
        with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
            with patch("src.services.ai_enrichment_service.update_job_ai_enrichment") as mock_update:
                
                # 3. Executamos o serviço
                result = await enrich_pending_jobs(mock_session, limit=1)
                
                # 4. Asserções
                assert result["processed"] == 1
                mock_update.assert_called_once_with(
                    session=mock_session,
                    job_id="test-id",
                    fit_score=90,
                    fit_rationale="Você tem as skills necessárias.",
                    skills=["Python", "FastAPI"],
                    seniority_normalized="junior",
                    english_level=EnglishLevel.ADVANCED
                )