import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

STORAGE_STATE_PATH = "data/storage_state.json"


async def main() -> None:
    Path("data").mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale="pt-BR", timezone_id="America/Sao_Paulo")
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        input("Faça login manualmente e pressione Enter para salvar a sessão...")
        await context.storage_state(path=STORAGE_STATE_PATH)
        print(f"Sessão salva em {STORAGE_STATE_PATH}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
