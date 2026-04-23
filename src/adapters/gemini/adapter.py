from src.adapters.gemini.fetcher import GeminiFetcher
from src.utils.storage import save_ai_response


class GeminiAdapter:
    provider_name = "gemini"

    def __init__(self, fetcher: GeminiFetcher):
        self.fetcher = fetcher

    async def process_query(self, user_prompt: str) -> str:
        result = await self.fetcher.fetch_and_debug(user_prompt)
        save_ai_response(
            prompt=user_prompt,
            response=result["text"],
            chat_url=result.get("url"),
            provider=self.provider_name,
            metadata={"selector_used": result.get("selector_used")},
        )
        return result["text"]
