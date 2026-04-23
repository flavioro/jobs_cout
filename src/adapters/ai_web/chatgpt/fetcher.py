from src.adapters.ai_web.base.fetcher import BaseAIWebFetcher
from src.adapters.ai_web.chatgpt.selectors import CHATGPT_SELECTORS


class ChatGPTWebFetcher(BaseAIWebFetcher):
    provider_name = "chatgpt"
    app_url_setting_name = "chatgpt_app_url"
    chat_mode_setting_name = "chatgpt_chat_mode"
    chat_url_setting_name = "chatgpt_chat_url"
    response_wait_setting_name = "chatgpt_response_wait_s"
    prompt_timeout_setting_name = "chatgpt_prompt_timeout_ms"
    debug_prefix = "chatgpt"
    selectors = CHATGPT_SELECTORS
