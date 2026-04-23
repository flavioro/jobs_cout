from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./data/jobscout.db"
    raw_html_dir: str = "data/raw_html"
    storage_state_path: str = "data/storage_state.json"

    google_storage_state_path: str = "data/google_storage_state.json"
    google_login_url: str = "https://accounts.google.com/ServiceLogin"

    ai_provider_default: str = "chatgpt"
    ai_debug_dir: str = "data/debug"
    chatgpt_storage_state_path: str = "data/gpt_profile"
    chatgpt_app_url: str = "https://chatgpt.com"
    gemini_storage_state_path: str = "data/gemini_profile"
    gemini_app_url: str = "https://gemini.google.com/app?pli=1"
    gemini_prompt_timeout_ms: int = 15000
    gemini_response_wait_s: float = 8.0

    parser_version: str = "linkedin_v1.0"

    # Adicione junto das outras variáveis do Playwright
    interactive_login: bool = False

    log_level: str = "INFO"

    playwright_headless: bool = True
    playwright_timeout_ms: int = 30000
    fetch_min_delay_s: float = 2.0
    fetch_max_delay_s: float = 5.0

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "changeme"

    save_screenshot_on_fetch: bool = False

    # --- Fase 1: Blocklist ---
    job_title_blocklist: str = ""

    # --- Fase 2: IA & Groq ---
    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"
    user_profile_context: str = ""

    @property
    def parsed_title_blocklist(self) -> List[str]:
        if not self.job_title_blocklist:
            return []
        return [word.strip().lower() for word in self.job_title_blocklist.split(",") if word.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()