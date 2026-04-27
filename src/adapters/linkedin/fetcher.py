import asyncio
import random
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.core.config import get_settings
from src.core.contracts import RawPage


async def _random_delay() -> None:
    settings = get_settings()
    delay = random.uniform(settings.fetch_min_delay_s, settings.fetch_max_delay_s)
    await asyncio.sleep(delay)


class LinkedInBrowserSession:
    """Reutiliza uma única sessão Playwright para múltiplas vagas do LinkedIn."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = (
            self.settings.storage_state_path
            if Path(self.settings.storage_state_path).exists()
            else None
        )
        self._playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self) -> "LinkedInBrowserSession":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def open(self) -> None:
        if self.page is not None:
            return

        print(f"[DEBUG] PLAYWRIGHT_HEADLESS = {self.settings.playwright_headless}")
        print(f"[DEBUG] STORAGE_STATE_PATH = {self.settings.storage_state_path}")
        print(f"[DEBUG] STORAGE_EXISTS = {bool(self.storage)}")

        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.settings.playwright_headless,
            slow_mo=500 if not self.settings.playwright_headless else 0,
        )
        self.context = await self.browser.new_context(
            storage_state=self.storage,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.settings.playwright_timeout_ms)

    async def close(self) -> None:
        """Fecha os recursos do Playwright de forma idempotente."""
        page = self.page
        context = self.context
        browser = self.browser
        playwright = self._playwright

        self.page = None
        self.context = None
        self.browser = None
        self._playwright = None

        try:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass
        finally:
            if playwright is not None:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    async def _recover_if_blocked(self, target_url: str) -> None:
        assert self.page is not None
        assert self.context is not None
        page = self.page

        current_url = page.url.lower()
        page_title = (await page.title()).lower()
        html_content_lower = (await page.content()).lower()

        is_blocked_url = any(term in current_url for term in ["/login", "/checkpoint", "/authwall"])
        is_blocked_title = any(term in page_title for term in ["olá novamente", "sign in", "entrar"])
        is_guest_view = "d_jobs_guest_details" in html_content_lower or "para se cadastrar ou entrar" in html_content_lower

        if is_blocked_url or is_blocked_title or is_guest_view:
            if self.settings.interactive_login and not self.settings.playwright_headless:
                print("\n" + "!" * 70)
                print("🚨 BLOQUEIO DETECTADO: O LinkedIn exige login ou captcha! 🚨")
                print("Acesse a janela do navegador agora, faça o login e resolva os desafios.")
                print("!" * 70 + "\n")

                await asyncio.to_thread(
                    input,
                    "👉 Após carregar o feed do LinkedIn, pressione [ENTER] aqui para continuar... ",
                )

                print("\n✅ Sessão recuperada! Atualizando storage_state.json...")
                if self.settings.storage_state_path:
                    await self.context.storage_state(path=self.settings.storage_state_path)

                print(f"🔄 Recarregando a vaga: {target_url}")
                await page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.playwright_timeout_ms,
                )
                await page.wait_for_timeout(3000)
            else:
                print("\n⚠️ Bloqueio detectado, mas INTERACTIVE_LOGIN está OFF ou em modo Headless.")

    async def fetch(self, url: str) -> RawPage:
        if self.page is None:
            await self.open()
        assert self.page is not None
        page = self.page

        await _random_delay()
        await page.goto(url, wait_until="domcontentloaded", timeout=self.settings.playwright_timeout_ms)
        await page.wait_for_timeout(3000)

        await self._recover_if_blocked(url)

        final_url = page.url
        page_title = await page.title()
        html = await page.content()

        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "final_url.txt").write_text(final_url, encoding="utf-8")
        (debug_dir / "page_title.txt").write_text(page_title, encoding="utf-8")
        (debug_dir / "linkedin_page.html").write_text(html, encoding="utf-8")

        apply_url = await capture_apply_url(page, html)

        screenshot_path = None
        if self.settings.save_screenshot_on_fetch:
            shots_dir = Path("data/screenshots")
            shots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(shots_dir / f"fetch_{random.randint(10,99)}.png")
            await page.screenshot(path=screenshot_path, full_page=True)

        if not self.settings.playwright_headless:
            await page.wait_for_timeout(2000)

        return RawPage(
            url=url,
            final_url=final_url,
            html=html,
            title=page_title,
            screenshot_path=screenshot_path,
            storage_state_used=bool(self.storage),
            apply_url=apply_url,
        )


async def fetch_linkedin_page(url: str) -> RawPage:
    async with LinkedInBrowserSession() as session:
        return await session.fetch(url)


async def capture_apply_url(page, html: str | None = None) -> str | None:
    html_lower = (html or "").lower()
    if "não aceita mais candidaturas" in html_lower or "nao aceita mais candidaturas" in html_lower:
        return None

    candidates = [
        page.get_by_role("button", name="Candidatar-se"),
        page.get_by_role("link", name="Candidatar-se"),
        page.get_by_role("button", name="Apply"),
        page.get_by_role("link", name="Apply"),
    ]

    for locator in candidates:
        try:
            if await locator.count() == 0:
                continue
            if not await locator.first.is_visible():
                continue
            async with page.expect_popup(timeout=4000) as popup_info:
                await locator.first.click()
            popup = await popup_info.value
            popup_url = popup.url
            await popup.close()
            return popup_url
        except Exception:
            continue

    return None
