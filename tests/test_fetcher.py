import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Adicione MagicMock aqui
from src.adapters.linkedin.fetcher import fetch_linkedin_page

@pytest.mark.asyncio
async def test_fetch_linkedin_page_triggers_interactive_login_on_guest_view(monkeypatch):
    """
    Garante que a deteção de Shadow Ban (Guest View) aciona a pausa
    para o login manual, atualiza o storage e recarrega a página.
    """
    
    # 1. Isolamos as configurações para forçar o cenário interativo
    class MockSettings:
        fetch_min_delay_s = 0.0
        fetch_max_delay_s = 0.0
        storage_state_path = "dummy_state.json"
        playwright_headless = False
        interactive_login = True
        playwright_timeout_ms = 1000
        save_screenshot_on_fetch = False

    monkeypatch.setattr("src.adapters.linkedin.fetcher.get_settings", lambda: MockSettings())
    monkeypatch.setattr("src.adapters.linkedin.fetcher.Path.exists", lambda self: True)

    # 2. Construímos o Mock do Playwright (Navegador, Contexto e Página)
    mock_page = AsyncMock()
    mock_page.set_default_timeout = MagicMock() # <--- CORREÇÃO: Força este método a ser síncrono
    mock_page.url = "https://www.linkedin.com/jobs/view/123"
    mock_page.title.return_value = "Desenvolvedor Python"
        
    # AQUI ESTÁ A ARMADILHA: Simulamos o HTML que o LinkedIn devolve quando aplica o Shadow Ban
    mock_page.content.return_value = '<html><meta name="pageKey" content="d_jobs_guest_details"></html>'

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    # Criamos um Context Manager assíncrono para o async_playwright()
    class AsyncPlaywrightCM:
        async def __aenter__(self): return mock_playwright
        async def __aexit__(self, *args): pass

    # 3. Aplicamos os Patches e executamos a função
    with patch("src.adapters.linkedin.fetcher.async_playwright", return_value=AsyncPlaywrightCM()):
        # Mock crucial: Simulamos o input() do terminal para não travar o teste
        with patch("src.adapters.linkedin.fetcher.asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            with patch("src.adapters.linkedin.fetcher.capture_apply_url", return_value="http://apply.com"):

                # Executamos o fetcher
                await fetch_linkedin_page("https://www.linkedin.com/jobs/view/123")

                # 4. Asserções (Verificamos se o script se comportou como deveria)
                
                # Garante que o terminal pediu o "Enter" ao utilizador
                mock_input.assert_called_once()
                
                # Garante que gravou o novo ficheiro de sessão após o Enter
                mock_context.storage_state.assert_called_once_with(path="dummy_state.json")
                
                # Garante que a função recarregou a página da vaga original (chamou goto 2 vezes: inicial + recarregamento)
                assert mock_page.goto.call_count == 2