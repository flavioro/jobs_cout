from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.ai_web.base.models import AIResponse
from src.services.browser_ai_service import run_browser_ai_prompt


@pytest.mark.asyncio
async def test_run_browser_ai_prompt_uses_factory():
    adapter = AsyncMock()
    adapter.process_query.return_value = AIResponse(text="ok", provider="gemini", chat_url="url")

    with patch("src.services.browser_ai_service.AIAdapterFactory.get_adapter", return_value=adapter) as factory:
        result = await run_browser_ai_prompt("gemini", object(), "oi")

    factory.assert_called_once()
    assert result.text == "ok"
