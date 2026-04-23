from src.adapters.ai_factory import AIAdapterFactory
from src.adapters.ai_web.base.models import AIChatOptions, AIResponse


async def run_browser_ai_prompt(provider: str, page, prompt: str, options: AIChatOptions | None = None) -> AIResponse:
    adapter = AIAdapterFactory.get_adapter(provider, page)
    return await adapter.process_query(prompt, options=options)
