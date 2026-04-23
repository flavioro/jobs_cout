from src.adapters.ai_web.base.adapter import BaseAIWebAdapter
from src.adapters.ai_web.base.models import AIChatOptions, AIResponse
from src.utils.storage import save_ai_response


class ChatGPTWebAdapter(BaseAIWebAdapter):
    provider_name = "chatgpt"

    def __init__(self, fetcher):
        self.fetcher = fetcher

    async def process_query(self, prompt: str, options: AIChatOptions | None = None) -> AIResponse:
        response = await self.fetcher.submit_prompt(prompt, options=options)
        save_ai_response(
            prompt=prompt,
            response=response.text,
            provider=response.provider,
            chat_url=response.chat_url,
            success=response.success,
            metadata=response.metadata,
            error=response.error,
        )
        return response
