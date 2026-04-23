import pytest

from src.adapters.ai_web.factory import AIAdapterFactory
from src.adapters.ai_web.chatgpt.adapter import ChatGPTWebAdapter
from src.adapters.ai_web.gemini.adapter import GeminiWebAdapter


class DummyPage:
    pass


def test_ai_factory_returns_chatgpt_adapter():
    adapter = AIAdapterFactory.get_adapter("chatgpt", DummyPage())
    assert isinstance(adapter, ChatGPTWebAdapter)


def test_ai_factory_returns_gemini_adapter():
    adapter = AIAdapterFactory.get_adapter("gemini", DummyPage())
    assert isinstance(adapter, GeminiWebAdapter)


def test_ai_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        AIAdapterFactory.get_adapter("claude", DummyPage())
