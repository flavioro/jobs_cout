import asyncio
import random
from pathlib import Path

from playwright.async_api import async_playwright

from src.core.config import get_settings
from src.core.contracts import RawPage


async def _random_delay() -> None:
    settings = get_settings()
    delay = random.uniform(settings.fetch_min_delay_s, settings.fetch_max_delay_s)
    await asyncio.sleep(delay)


async def fetch_linkedin_page(url: str) -> RawPage:
    settings = get_settings()
    storage = settings.storage_state_path if Path(settings.storage_state_path).exists() else None

    print(f"[DEBUG] PLAYWRIGHT_HEADLESS = {settings.playwright_headless}")
    print(f"[DEBUG] STORAGE_STATE_PATH = {settings.storage_state_path}")
    print(f"[DEBUG] STORAGE_EXISTS = {bool(storage)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=settings.playwright_headless,
            slow_mo=500 if not settings.playwright_headless else 0,
        )

        context = await browser.new_context(
            storage_state=storage,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()
        page.set_default_timeout(settings.playwright_timeout_ms)

        await _random_delay()
        await page.goto(url, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)
        await page.wait_for_timeout(3000)

        final_url = page.url
        page_title = await page.title()
        html = await page.content()

        print(f"[DEBUG] FINAL_URL = {final_url}")
        print(f"[DEBUG] PAGE_TITLE = {page_title}")

        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

        (debug_dir / "final_url.txt").write_text(final_url, encoding="utf-8")
        (debug_dir / "page_title.txt").write_text(page_title, encoding="utf-8")
        (debug_dir / "linkedin_page.html").write_text(html, encoding="utf-8")
        await page.screenshot(path=str(debug_dir / "linkedin_page.png"), full_page=True)

        ready_signals = [
            "Sobre a vaga",
            "Candidatar-se",
            "Candidate-se",
            "Não aceita mais candidaturas",
            'data-testid="expandable-text-box"',
            'href="/company/',
            "Mais vagas",
        ]
        print(f"[DEBUG] READY_SIGNAL_FOUND = {any(signal in html for signal in ready_signals)}")

        apply_url = await capture_apply_url(page, html)

        screenshot_path = None
        if settings.save_screenshot_on_fetch:
            shots_dir = Path("data/screenshots")
            shots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(shots_dir / "last_fetch.png")
            await page.screenshot(path=screenshot_path, full_page=True)

        if not settings.playwright_headless:
            await page.wait_for_timeout(2000)

        final_url = page.url
        html = await page.content()
        title = await page.title()

        await context.close()
        await browser.close()

        return RawPage(
            url=url,
            final_url=final_url,
            html=html,
            title=title,
            screenshot_path=screenshot_path,
            storage_state_used=bool(storage),
            apply_url=apply_url,
        )


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
