from unittest.mock import AsyncMock

import pytest

from src.adapters.ai_web.base.fetcher import BaseAIWebFetcher
from src.adapters.ai_web.base.models import AIChatOptions


class FakeSettings:
    fake_app_url = "https://example.com/app"
    fake_chat_mode = "new_chat"
    fake_chat_url = None
    fake_prompt_timeout_ms = 10
    fake_response_wait_s = 0.01


class DummyFetcher(BaseAIWebFetcher):
    provider_name = "fake"
    app_url_setting_name = "fake_app_url"
    chat_mode_setting_name = "fake_chat_mode"
    chat_url_setting_name = "fake_chat_url"
    response_wait_setting_name = "fake_response_wait_s"
    prompt_timeout_setting_name = "fake_prompt_timeout_ms"
    debug_prefix = "fake"
    selectors = {
        "prompt_input": ["primary", "fallback"],
        "response_blocks": ["response"],
        "stop_button": ["stop"],
        "send_button": [],
        "new_chat": [],
    }

    def __init__(self, page):
        super().__init__(page)
        self.settings = FakeSettings()


class LocatorStub:
    def __init__(self, visible=False, count=0, texts=None):
        self.visible = visible
        self._count = count
        self.texts = texts or []
        self.first = self

    async def wait_for(self, state="visible", timeout=0):
        if state == "visible" and not self.visible:
            raise TimeoutError("not visible")
        return None

    async def count(self):
        return self._count

    def nth(self, index):
        item = AsyncMock()
        item.inner_text.return_value = self.texts[index]
        return item

    async def click(self):
        return None

    async def fill(self, value):
        return None


class PageStub:
    def __init__(self, mapping):
        self.mapping = mapping
        self.url = "https://example.com/chat/1"
        self.keyboard = AsyncMock()
        self.goto = AsyncMock()
        self.wait_for_load_state = AsyncMock()
        self.reload = AsyncMock()
        self.content = AsyncMock(return_value="<html></html>")
        self.screenshot = AsyncMock()

    def locator(self, selector):
        return self.mapping[selector]


@pytest.mark.asyncio
async def test_first_visible_locator_uses_fallback_selector():
    page = PageStub({
        "primary": LocatorStub(visible=False),
        "fallback": LocatorStub(visible=True),
        "response": LocatorStub(count=0),
        "stop": LocatorStub(visible=False),
    })
    fetcher = DummyFetcher(page)

    locator, selector = await fetcher._first_visible_locator(["primary", "fallback"], timeout_ms=10)

    assert selector == "fallback"
    assert locator is page.mapping["fallback"]


@pytest.mark.asyncio
async def test_submit_prompt_returns_only_new_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = PageStub({
        "primary": LocatorStub(visible=True),
        "fallback": LocatorStub(visible=False),
        "response": LocatorStub(count=2, texts=["resposta antiga", "Show thinking\nresposta nova"]),
        "stop": LocatorStub(visible=False),
    })
    fetcher = DummyFetcher(page)

    fetcher._count_existing_responses = AsyncMock(return_value=1)

    result = await fetcher.submit_prompt("oi", AIChatOptions(max_retries=0, response_timeout_s=0.01))

    assert result.success is True
    assert result.text == "resposta nova"
    page.keyboard.press.assert_awaited_with("Enter")


@pytest.mark.asyncio
async def test_submit_prompt_can_use_existing_chat_url(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = PageStub({
        "primary": LocatorStub(visible=True),
        "fallback": LocatorStub(visible=False),
        "response": LocatorStub(count=1, texts=["resposta nova"]),
        "stop": LocatorStub(visible=False),
    })
    fetcher = DummyFetcher(page)
    fetcher._count_existing_responses = AsyncMock(return_value=0)

    options = AIChatOptions(mode="existing_chat", existing_chat_url="https://example.com/chat/existing", max_retries=0, response_timeout_s=0.01)
    await fetcher.submit_prompt("oi", options)

    page.goto.assert_awaited_with("https://example.com/chat/existing", wait_until="domcontentloaded")
