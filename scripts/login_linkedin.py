import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from src.core.config import get_settings


async def main() -> None:
    settings = get_settings()
    user_data_dir = Path(settings.linkedin_profile_path)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 960},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        input("Faça login manualmente no LinkedIn e pressione Enter para manter a sessão persistente... ")
        print(f"Perfil persistente salvo em {user_data_dir}")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
