import asyncio
from pathlib import Path

from playwright.async_api import Page

from src.adapters.gemini.selectors import GEMINI_SELECTORS
from src.core.config import get_settings


import asyncio
from pathlib import Path

from playwright.async_api import Page

from src.adapters.gemini.selectors import GEMINI_SELECTORS
from src.core.config import get_settings


class GeminiFetcher:
    def __init__(self, page: Page):
        self.page = page
        self.settings = get_settings()

    async def _first_visible_locator(self, selectors: list[str], timeout_ms: int = 4000):
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=timeout_ms)
                return locator, selector
            except Exception:
                continue
        return None, None

    async def _extract_last_response(self) -> str:
        texts: list[str] = []
        for selector in GEMINI_SELECTORS["response_blocks"]:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                if count <= 0:
                    continue
                for idx in range(count):
                    text = (await locator.nth(idx).inner_text()).strip()
                    if text:
                        texts.append(text)
            except Exception:
                continue

        if texts:
            return texts[-1]
        return "Falha na captura da resposta do Gemini."

    async def fetch_and_debug(self, prompt: str) -> dict[str, str]:
        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

        try:
            await self.page.goto(self.settings.gemini_app_url, wait_until="domcontentloaded")

            try:
                await self.page.wait_for_load_state("load", timeout=10000)
            except Exception:
                pass

            await asyncio.sleep(2)

            prompt_locator, selector_used = await self._first_visible_locator(
                GEMINI_SELECTORS["prompt_input"],
                timeout_ms=self.settings.gemini_prompt_timeout_ms,
            )
            if prompt_locator is None:
                raise RuntimeError("Não foi possível localizar o campo de prompt do Gemini.")

            await prompt_locator.click()
            await prompt_locator.fill(prompt)
            await self.page.keyboard.press("Enter")

            stop_locator, _ = await self._first_visible_locator(
                GEMINI_SELECTORS["stop_button"],
                timeout_ms=5000,
            )

            if stop_locator is not None:
                try:
                    await stop_locator.wait_for(state="hidden", timeout=self.settings.playwright_timeout_ms)
                except Exception:
                    await asyncio.sleep(self.settings.gemini_response_wait_s)
            else:
                await asyncio.sleep(self.settings.gemini_response_wait_s)

            await asyncio.sleep(1)
            final_text = await self._extract_last_response()

            return {
                "text": final_text.strip(),
                "url": self.page.url,
                "selector_used": selector_used or "unknown",
            }
        finally:
            content = await self.page.content()
            with open(debug_dir / "gemini_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            await self.page.screenshot(path=str(debug_dir / "gemini_page.png"), full_page=True)