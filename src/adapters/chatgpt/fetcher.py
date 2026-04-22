# src/adapters/chatgpt/fetcher.py
import asyncio
from pathlib import Path
from src.core.config import get_settings
from src.adapters.chatgpt.selectors import CHATGPT_SELECTORS

class ChatGPTFetcher:
    def __init__(self, page):
        self.page = page
        self.settings = get_settings()

    async def fetch_and_debug(self, prompt: str):
        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. Navegação
            print(f"🚀 Navegando para ChatGPT...")
            await self.page.goto("https://chatgpt.com")
            
            # 2. Lidar com obstáculos iniciais (Cookies)
            try:
                cookie_button = self.page.get_by_role("button", name="Aceitar todos")
                if await cookie_button.is_visible(timeout=5000):
                    await cookie_button.click()
                    print("✅ Banner de cookies fechado.")
            except:
                pass

            # >>> PAUSA PARA INTERAÇÃO NO CMD <<<
            print("\n" + "!"*60)
            print("PAUSA DE SEGURANÇA:")
            print("1. Verifique se o login está ativo (sua foto/iniciais no canto).")
            print("2. Feche manualmente qualquer pop-up que esteja na frente.")
            print("!"*60)
            input("Pressione [ENTER] aqui no CMD para enviar a pergunta ao ChatGPT...")
            print("Enviando prompt agora...")

            # 3. Envio do Prompt
            await self.page.wait_for_selector(CHATGPT_SELECTORS["prompt_textarea"])
            await self.page.click(CHATGPT_SELECTORS["prompt_textarea"])
            await self.page.keyboard.type(prompt, delay=50)
            await self.page.keyboard.press("Enter")
            print("🚀 Prompt enviado. Sincronizando com a IA...")

            # --- NOVA LÓGICA DE ESPERA ROBUSTA ---
            
            # Passo A: Espera o botão de STOP aparecer (garante que a IA começou a responder)
            try:
                await self.page.wait_for_selector(CHATGPT_SELECTORS["stop_button"], timeout=5000)
                print("⏳ IA começou a gerar o texto...")
            except:
                # Se a resposta for muito rápida, o botão pode nem aparecer
                print("⚠️ IA respondeu muito rápido ou botão de stop não detectado.")

            # Passo B: Espera o botão de STOP sumir (garante que a IA terminou de escrever)
            await self.page.wait_for_selector(
                CHATGPT_SELECTORS["stop_button"], 
                state="hidden", 
                timeout=self.settings.playwright_timeout_ms
            )
            print("✅ IA finalizou a resposta.")
            
            # Pequena pausa extra para o DOM estabilizar e evitar pegar botões de interface
            await asyncio.sleep(1)

	    # 5. Extração do Texto e da URL
            responses = self.page.locator(CHATGPT_SELECTORS["last_response"])
            count = await responses.count()
            
            final_text = "Falha na captura"
            if count > 0:
                final_text = await responses.nth(count - 1).inner_text()
            
            # Captura a URL atual (que agora contém o ID da conversa)
            current_url = self.page.url # Ex: https://chatgpt.com/c/69e8cdd2...
            
            return {
                "text": final_text.strip(),
                "url": current_url
            }

        except Exception as e:
            print(f"❌ ERRO DURANTE O PROCESSO: {e}")
            return f"Erro na captura: {e}"

        finally:
            # Garante que sempre teremos o print do que aconteceu
            print(f"📸 Gravando arquivos de debug...")
            content = await self.page.content()
            with open(debug_dir / "chatgpt_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            await self.page.screenshot(path=str(debug_dir / "chatgpt_page.png"), full_page=True)