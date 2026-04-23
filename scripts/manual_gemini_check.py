import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from src.adapters.ai_web.factory import AIAdapterFactory
from src.core.config import get_settings
from src.core.prompts_ai import get_ai_prompt


async def run_test():
    settings = get_settings()
    user_data_dir = Path(settings.gemini_storage_state_path)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
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

        page = context.pages[0] if context.pages else await context.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        adapter = AIAdapterFactory.get_adapter("gemini", page)
        pergunta = get_ai_prompt("test_connection", provider="gemini")
        resposta = await adapter.process_query(pergunta)

        print("\n" + "=" * 50)
        print("🤖 RESPOSTA FINAL:")
        print(resposta.text if hasattr(resposta, "text") else resposta)
        print("=" * 50)

        try:
            await context.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_test())
