import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from src.services.ai_enrichment_service import enrich_pending_jobs
from src.core.enums import EnglishLevel, JobSector

@pytest.mark.asyncio
async def test_enrich_pending_jobs_extracts_and_saves_sector():
    # 1. Configuração dos Mocks
    mock_session = AsyncMock()
    
    # Criamos um objeto Mock que se comporta como um modelo SQLAlchemy
    mock_job = MagicMock()
    mock_job.id = "test-sector-id"
    mock_job.title = "Python Developer"
    mock_job.company = "Nubank"
    mock_job.description_text = "Vaga tech no setor financeiro"
    mock_job.seniority_normalized = None
    mock_job.sector = None 

    # Resposta simulada da IA
    class MockAnalysis:
        skills = ["Python"]
        fit_score = 80
        fit_rationale = "Bom fit"
        seniority_suggestion = "Pleno"
        english_level = "advanced"
        sector = "Finanças, Bancos e Fintechs"

    # Patches para evitar chamadas reais
    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
        with patch("src.services.ai_enrichment_service.GroqJobAnalysis.model_validate_json") as mock_val:
            mock_val.return_value = MockAnalysis()
            
            with patch("src.services.ai_enrichment_service.AsyncGroq") as mock_groq:
                # Mock da resposta da API
                mock_groq.return_value.chat.completions.create = AsyncMock()
                
                with patch("src.services.ai_enrichment_service.update_job_ai_enrichment") as mock_update:
                    # Execução
                    await enrich_pending_jobs(mock_session, limit=1)
                    
                    # Verificação: O serviço chamou a persistência com o setor correto?
                    mock_update.assert_called_once()
                    args, kwargs = mock_update.call_args
                    assert kwargs["sector"] == "Finanças, Bancos e Fintechs"

@pytest.mark.asyncio
async def test_enrich_pending_jobs_updates_db_correctly(tmp_path, monkeypatch):
    class MockSettings:
        parsed_title_blocklist = []
        groq_api_key = "fake-key"
        groq_model = "llama-3.3"
        user_profile_context = "Perfil Mock"
    
    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="""
        {
            "skills": ["Python", "FastAPI"],
            "fit_score": 90,
            "fit_rationale": "Você tem as skills necessárias.",
            "seniority_suggestion": "junior",
            "english_level": "advanced",
            "sector": "Consultoria de TI e Outsourcing"
        }
        """))
    ]

    with patch("src.services.ai_enrichment_service.AsyncGroq") as mock_groq:
        mock_groq.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_session = AsyncMock()
        mock_job = AsyncMock()
        mock_job.id = "test-id"
        mock_job.title = "Python Developer"
        mock_job.company = "Tech Corp"
        mock_job.description_text = "Vaga para Python e FastAPI"
        mock_job.seniority_normalized = None

        with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
            with patch("src.services.ai_enrichment_service.update_job_ai_enrichment") as mock_update:
                
                result = await enrich_pending_jobs(mock_session, limit=1)
                
                assert result["processed"] == 1
                # ATUALIZADO: Agora incluímos o sector na verificação da chamada
                mock_update.assert_called_once_with(
                    session=mock_session,
                    job_id="test-id",
                    fit_score=90,
                    fit_rationale="Você tem as skills necessárias.",
                    skills=["Python", "FastAPI"],
                    seniority_normalized="junior",
                    english_level=EnglishLevel.ADVANCED,
                    sector="Consultoria de TI e Outsourcing" # <-- Campo adicionado
                )