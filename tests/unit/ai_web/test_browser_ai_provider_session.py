from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.ai_web.base.models import AIResponse
from src.services.browser_ai_service import BrowserAIProviderSession


@pytest.mark.asyncio
async def test_browser_ai_provider_session_uses_factory_and_closes_playwright(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    page = AsyncMock()
    page.add_init_script = AsyncMock()
    context = AsyncMock()
    context.pages = [page]
    context.close = AsyncMock()
    chromium = AsyncMock()
    chromium.launch_persistent_context = AsyncMock(return_value=context)
    playwright = AsyncMock()
    playwright.chromium = chromium
    playwright.stop = AsyncMock()

    adapter = AsyncMock()
    adapter.process_query = AsyncMock(return_value=AIResponse(text="ok", provider="gemini", chat_url="url"))

    async_playwright_manager = AsyncMock()
    async_playwright_manager.start = AsyncMock(return_value=playwright)

    with patch("src.services.browser_ai_service.async_playwright", return_value=async_playwright_manager):
        with patch("src.services.browser_ai_service.AIAdapterFactory.get_adapter", return_value=adapter):
            async with BrowserAIProviderSession("gemini") as session:
                result = await session.run_prompt("teste")

    assert result.text == "ok"
    chromium.launch_persistent_context.assert_awaited()
    playwright.stop.assert_awaited_once()
