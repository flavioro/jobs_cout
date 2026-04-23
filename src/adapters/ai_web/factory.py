from src.adapters.ai_web.chatgpt.adapter import ChatGPTWebAdapter
from src.adapters.ai_web.chatgpt.fetcher import ChatGPTWebFetcher
from src.adapters.ai_web.gemini.adapter import GeminiWebAdapter
from src.adapters.ai_web.gemini.fetcher import GeminiWebFetcher


class AIAdapterFactory:
    @staticmethod
    def get_adapter(provider: str, page):
        provider_key = provider.strip().lower()
        if provider_key == "chatgpt":
            return ChatGPTWebAdapter(ChatGPTWebFetcher(page))
        if provider_key == "gemini":
            return GeminiWebAdapter(GeminiWebFetcher(page))
        raise ValueError(f"Provider de IA não suportado: {provider}")
