from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.ai_web.base.models import AIResponse
from src.adapters.ai_web.chatgpt.adapter import ChatGPTWebAdapter
from src.adapters.ai_web.gemini.adapter import GeminiWebAdapter


@pytest.mark.asyncio
async def test_chatgpt_adapter_logs_structured_response():
    fetcher = AsyncMock()
    fetcher.submit_prompt.return_value = AIResponse(
        text="ok",
        provider="chatgpt",
        chat_url="https://chatgpt.com/c/1",
        metadata={"selector_used": "#prompt-textarea"},
    )

    with patch("src.adapters.ai_web.chatgpt.adapter.save_ai_response") as save_log:
        adapter = ChatGPTWebAdapter(fetcher)
        result = await adapter.process_query("teste")

    assert result.text == "ok"
    save_log.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_adapter_logs_errors_without_breaking():
    fetcher = AsyncMock()
    fetcher.submit_prompt.return_value = AIResponse(
        text="",
        provider="gemini",
        chat_url="https://gemini.google.com/app/1",
        success=False,
        error="timeout",
        metadata={"retries": 2},
    )

    with patch("src.adapters.ai_web.gemini.adapter.save_ai_response") as save_log:
        adapter = GeminiWebAdapter(fetcher)
        result = await adapter.process_query("teste")

    assert result.success is False
    assert result.error == "timeout"
    save_log.assert_called_once()
