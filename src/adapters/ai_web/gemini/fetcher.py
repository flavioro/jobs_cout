from src.adapters.ai_web.base.fetcher import BaseAIWebFetcher
from src.adapters.ai_web.gemini.selectors import GEMINI_SELECTORS


class GeminiWebFetcher(BaseAIWebFetcher):
    provider_name = "gemini"
    app_url_setting_name = "gemini_app_url"
    chat_mode_setting_name = "gemini_chat_mode"
    chat_url_setting_name = "gemini_chat_url"
    response_wait_setting_name = "gemini_response_wait_s"
    prompt_timeout_setting_name = "gemini_prompt_timeout_ms"
    debug_prefix = "gemini"
    selectors = GEMINI_SELECTORS
