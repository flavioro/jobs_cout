# src/adapters/chatgpt/adapter.py
from src.adapters.chatgpt.fetcher import ChatGPTFetcher
from src.utils.storage import save_ai_response

class ChatGPTAdapter:
    def __init__(self, fetcher: ChatGPTFetcher):
        self.fetcher = fetcher

    async def process_query(self, user_prompt: str):
        # 1. O fetcher agora retorna um dict {"text": "...", "url": "..."}
        result = await self.fetcher.fetch_and_debug(user_prompt)
        
        # 2. Gravamos no JSON incluindo a URL
        save_ai_response(
            prompt=user_prompt, 
            response=result["text"], 
            chat_url=result["url"]
        )
        
        return result["text"]