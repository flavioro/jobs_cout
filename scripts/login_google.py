# scripts/login_google.py
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    # Criamos uma pasta física para o perfil
    user_data_dir = Path("data/gpt_profile")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Abrimos o contexto persistente (ele salva tudo automaticamente na pasta)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        
        page = context.pages[0]
        await page.goto("https://chatgpt.com")

        print("\n" + "!"*50)
        print("FAÇA LOGIN MANUALMENTE NO CHATGPT.")
        print("Certifique-se de que os chats apareceram e NÃO sumiram.")
        print("!"*50 + "\n")

        input("Após o ChatGPT estar estável, pressione [ENTER] para fechar...")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())