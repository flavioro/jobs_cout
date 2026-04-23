from __future__ import annotations

from abc import ABC, abstractmethod

from src.adapters.ai_web.base.models import AIChatOptions, AIResponse


class BaseAIWebAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def process_query(
        self,
        prompt: str,
        options: AIChatOptions | None = None,
    ) -> AIResponse:
        raise NotImplementedError
