import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.linkedin.fetcher import LinkedInBrowserSession, fetch_linkedin_page


@pytest.mark.asyncio
async def test_fetch_linkedin_page_triggers_interactive_login_on_guest_view(monkeypatch):
    """Garante que a deteção de Guest View aciona a recuperação interativa."""

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

    mock_page = AsyncMock()
    mock_page.set_default_timeout = MagicMock()
    mock_page.url = "https://www.linkedin.com/jobs/view/123"
    mock_page.title.return_value = "Desenvolvedor Python"
    mock_page.content.return_value = '<html><meta name="pageKey" content="d_jobs_guest_details"></html>'

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_manager = MagicMock()
    mock_manager.start = AsyncMock(return_value=mock_playwright)

    with patch("src.adapters.linkedin.fetcher.async_playwright", return_value=mock_manager):
        with patch("src.adapters.linkedin.fetcher.asyncio.to_thread", new_callable=AsyncMock) as mock_input:
            with patch("src.adapters.linkedin.fetcher.capture_apply_url", return_value="http://apply.com"):
                await fetch_linkedin_page("https://www.linkedin.com/jobs/view/123")

                mock_input.assert_called_once()
                mock_context.storage_state.assert_called_once_with(path="dummy_state.json")
                assert mock_page.goto.call_count == 2
                mock_playwright.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_linkedin_browser_session_close_uses_stop(monkeypatch):
    class MockSettings:
        fetch_min_delay_s = 0.0
        fetch_max_delay_s = 0.0
        storage_state_path = "dummy_state.json"
        playwright_headless = True
        interactive_login = False
        playwright_timeout_ms = 1000
        save_screenshot_on_fetch = False

    monkeypatch.setattr("src.adapters.linkedin.fetcher.get_settings", lambda: MockSettings())
    monkeypatch.setattr("src.adapters.linkedin.fetcher.Path.exists", lambda self: True)

    mock_page = AsyncMock()
    mock_page.set_default_timeout = MagicMock()

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_manager = MagicMock()
    mock_manager.start = AsyncMock(return_value=mock_playwright)

    with patch("src.adapters.linkedin.fetcher.async_playwright", return_value=mock_manager):
        session = LinkedInBrowserSession()
        await session.open()
        await session.close()

        mock_playwright.stop.assert_awaited_once()
        mock_context.close.assert_awaited_once()
        mock_browser.close.assert_awaited_once()
