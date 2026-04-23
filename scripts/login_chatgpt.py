import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from src.core.config import get_settings


async def main():
    settings = get_settings()
    user_data_dir = Path(settings.chatgpt_storage_state_path)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1280, "height": 720},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(settings.chatgpt_app_url, wait_until="domcontentloaded")

        print("Faça login manualmente no ChatGPT e confirme que a caixa de prompt está visível.")
        input("Quando terminar, pressione ENTER para fechar o navegador... ")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
