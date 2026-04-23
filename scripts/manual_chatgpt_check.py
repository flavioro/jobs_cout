# scripts/test_chatgpt.py
import asyncio
from pathlib import Path
from src.core.config import get_settings
from src.core.prompts_ai import get_ai_prompt
from src.adapters.chatgpt.fetcher import ChatGPTFetcher
from src.adapters.chatgpt.adapter import ChatGPTAdapter
from playwright.async_api import async_playwright

async def run_test():
    settings = get_settings()
    user_data_dir = Path("data/gpt_profile")

    async with async_playwright() as p:
        # Lançamento com argumentos de camuflagem (Stealth)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            # Argumentos vitais para não ser detectado pelo Cloudflare/OpenAI
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        # O contexto persistente já abre uma página por padrão
        page = context.pages[0] if context.pages else await context.new_page()

        # Injetamos um script para esconder o webdriver via JS
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        fetcher = ChatGPTFetcher(page)
        adapter = ChatGPTAdapter(fetcher)

        pergunta = get_ai_prompt("test_connection", provider="chatgpt")
        resposta = await adapter.process_query(pergunta)

        print("\n" + "="*50)
        print(f"🤖 RESPOSTA FINAL:\n{resposta}")
        print("="*50)

        # Usamos try/except para evitar o erro se você fechar a janela antes
        try:
            await context.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(run_test())