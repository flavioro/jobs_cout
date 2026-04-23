import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

from src.core.config import get_settings

async def main():
    settings = get_settings()
    user_data_dir = Path(settings.gemini_storage_state_path)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(settings.gemini_app_url)

        print("\n" + "!" * 50)
        print("FAÇA LOGIN MANUALMENTE NO GEMINI/GOOGLE.")
        print("Espere a tela principal do Gemini carregar completamente.")
        print("!" * 50 + "\n")

        input("Após o Gemini estar estável, pressione [ENTER] para fechar...")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())