
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.core.enums import EnglishLevel
from src.services.ai_enrichment_service import (
    _normalize_sector_value,
    _normalize_english_level,
    _normalize_seniority_suggestion,
    enrich_pending_jobs,
)


def test_normalize_sector_value_maps_non_enum_value():
    assert _normalize_sector_value("Consultoria de TI / Construção Civil") == "Consultoria de TI e Outsourcing"


def test_normalize_english_level_maps_not_mentioned_variants():
    assert _normalize_english_level("Não mencionado") == "not_mentioned"
    assert _normalize_english_level("NÒo mencionado") == "not_mentioned"


def test_normalize_seniority_suggestion_maps_portuguese_mid():
    assert _normalize_seniority_suggestion("Pleno") == "mid"


@pytest.mark.asyncio
async def test_enrich_pending_jobs_uses_gemini_web_provider(monkeypatch):
    mock_session = AsyncMock()
    mock_job = SimpleNamespace(
        id="job-web-1",
        title="Python Developer",
        company="Tech Corp",
        description_text="Python and FastAPI role",
        seniority_normalized=None,
        source="linkedin",
        url="https://linkedin.com/jobs/view/1",
    )

    class MockSettings:
        parsed_title_blocklist = []
        user_profile_context = "Perfil mock"
        enrichment_provider = "gemini_web"
        enrichment_web_chat_mode = "new_chat"
        enrichment_web_response_timeout_s = 0.5
        enrichment_web_max_retries = 0
        enrichment_web_force_new_chat = True

    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    fake_browser_session = AsyncMock()
    fake_browser_session.run_prompt.return_value = SimpleNamespace(
        success=True,
        text='{"skills": ["Python", "FastAPI"], "fit_score": 82, "fit_rationale": "Bom fit", "seniority_suggestion": "Pleno", "english_level": "NÒo mencionado", "sector": "Consultoria de TI / ConstruþÒo Civil"}',
    )

    browser_cm = AsyncMock()
    browser_cm.__aenter__.return_value = fake_browser_session
    browser_cm.__aexit__.return_value = None

    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
        with patch("src.services.ai_enrichment_service.update_job_ai_enrichment") as mock_update:
            with patch("src.services.ai_enrichment_service.BrowserAIProviderSession", return_value=browser_cm):
                result = await enrich_pending_jobs(mock_session, limit=1)

    assert result["provider"] == "gemini_web"
    assert result["processed"] == 1
    mock_update.assert_called_once_with(
        session=mock_session,
        job_id="job-web-1",
        fit_score=82,
        fit_rationale="Bom fit",
        skills=["Python", "FastAPI"],
        english_level=EnglishLevel.NOT_MENTIONED,
        seniority_normalized="mid",
        sector="Consultoria de TI e Outsourcing",
    )


@pytest.mark.asyncio
async def test_enrich_pending_jobs_handles_chatgpt_web_invalid_json(monkeypatch):
    mock_session = AsyncMock()
    mock_job = SimpleNamespace(
        id="job-web-2",
        title="Backend Developer",
        company="ACME",
        description_text="Role text",
        seniority_normalized=None,
        source="linkedin",
        url="https://linkedin.com/jobs/view/2",
    )

    class MockSettings:
        parsed_title_blocklist = []
        user_profile_context = "Perfil mock"
        enrichment_provider = "chatgpt_web"
        enrichment_web_chat_mode = "new_chat"
        enrichment_web_response_timeout_s = 0.5
        enrichment_web_max_retries = 0
        enrichment_web_force_new_chat = True

    monkeypatch.setattr("src.services.ai_enrichment_service.get_settings", lambda: MockSettings())

    fake_browser_session = AsyncMock()
    fake_browser_session.run_prompt.return_value = SimpleNamespace(
        success=True,
        text="Resposta sem JSON estruturado",
    )

    browser_cm = AsyncMock()
    browser_cm.__aenter__.return_value = fake_browser_session
    browser_cm.__aexit__.return_value = None

    with patch("src.services.ai_enrichment_service.get_pending_jobs_for_enrichment", return_value=[mock_job]):
        with patch("src.services.ai_enrichment_service.BrowserAIProviderSession", return_value=browser_cm):
            with patch("src.services.ai_enrichment_service.update_job_ai_enrichment") as mock_update:
                result = await enrich_pending_jobs(mock_session, limit=1)

    assert result["provider"] == "chatgpt_web"
    assert result["failed"] == 1
    mock_update.assert_not_called()
