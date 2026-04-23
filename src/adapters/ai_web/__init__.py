from src.adapters.ai_web.base import AIChatOptions, AIResponse
from src.adapters.ai_web.chatgpt.adapter import ChatGPTWebAdapter
from src.adapters.ai_web.chatgpt.fetcher import ChatGPTWebFetcher
from src.adapters.ai_web.gemini.adapter import GeminiWebAdapter
from src.adapters.ai_web.gemini.fetcher import GeminiWebFetcher

__all__ = [
    "AIChatOptions",
    "AIResponse",
    "ChatGPTWebAdapter",
    "ChatGPTWebFetcher",
    "GeminiWebAdapter",
    "GeminiWebFetcher",
]
