from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from src.adapters.ai_web.base.models import AIChatOptions, AIResponse
from src.adapters.ai_web.factory import AIAdapterFactory
from src.core.config import get_settings


def _provider_storage_path(provider: str) -> str:
    settings = get_settings()
    provider_key = provider.strip().lower()
    if provider_key == "chatgpt":
        return settings.chatgpt_storage_state_path
    if provider_key == "gemini":
        return settings.gemini_storage_state_path
    raise ValueError(f"Provider de IA não suportado: {provider}")


class BrowserAIProviderSession:
    def __init__(self, provider: str):
        self.provider = provider.strip().lower()
        self.settings = get_settings()
        self._playwright = None
        self._context = None
        self.page = None

    async def __aenter__(self) -> "BrowserAIProviderSession":
        user_data_dir = Path(_provider_storage_path(self.provider))
        user_data_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=self.settings.playwright_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )
        self.page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        await self.page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass

    async def run_prompt(self, prompt: str, options: AIChatOptions | None = None) -> AIResponse:
        if self.page is None:
            raise RuntimeError("Browser AI session was not initialized.")
        adapter = AIAdapterFactory.get_adapter(self.provider, self.page)
        return await adapter.process_query(prompt, options=options)


async def run_browser_ai_prompt(
    provider: str,
    page,
    prompt: str,
    options: AIChatOptions | None = None,
) -> AIResponse:
    adapter = AIAdapterFactory.get_adapter(provider, page)
    return await adapter.process_query(prompt, options=options)
