from playwright.async_api import Page

from src.adapters.chatgpt.adapter import ChatGPTAdapter
from src.adapters.chatgpt.fetcher import ChatGPTFetcher
from src.adapters.gemini.adapter import GeminiAdapter
from src.adapters.gemini.fetcher import GeminiFetcher


class AIAdapterFactory:
    @staticmethod
    def get_adapter(provider: str, page: Page):
        provider_normalized = provider.strip().lower()

        if provider_normalized == "chatgpt":
            return ChatGPTAdapter(ChatGPTFetcher(page))
        if provider_normalized == "gemini":
            return GeminiAdapter(GeminiFetcher(page))

        raise ValueError(f"Provider de IA não suportado: {provider}")
