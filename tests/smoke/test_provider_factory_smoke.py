import pytest

from src.adapters.ai_web.factory import AIAdapterFactory


class DummyPage:
    pass


@pytest.mark.smoke
def test_provider_factory_smoke_chatgpt_and_gemini():
    assert AIAdapterFactory.get_adapter("chatgpt", DummyPage()) is not None
    assert AIAdapterFactory.get_adapter("gemini", DummyPage()) is not None
