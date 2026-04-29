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
    linkedin_profile_path: str = "data/linkedin_profile"
    linkedin_search_urls_path: str = "data/linkedin_search_urls.json"
    linkedin_search_scroll_steps: int = 8
    linkedin_search_scroll_delay_s: float = 1.5
    linkedin_search_initial_wait_s: float = 2.0
    linkedin_search_detail_wait_s: float = 1.5
    linkedin_search_stable_scroll_rounds: int = 3
    linkedin_search_card_limit_per_url: int = 25
    linkedin_search_export_xlsx_enabled: bool = True
    linkedin_search_export_xlsx_path: str = "data/exports/linkedin_search_cards.xlsx"
    linkedin_search_skip_closed: bool = True

    google_storage_state_path: str = "data/google_storage_state.json"
    google_login_url: str = "https://accounts.google.com/ServiceLogin"

    csv_import_default_path: str = "data/imports/jobs_last_2_days.csv"
    csv_import_status_filter: str = "new"

    chatgpt_storage_state_path: str = "data/gpt_profile"
    chatgpt_app_url: str = "https://chatgpt.com"
    chatgpt_chat_mode: str = "new_chat"
    chatgpt_chat_url: str | None = None
    chatgpt_prompt_timeout_ms: int = 5000
    chatgpt_response_wait_s: float = 10.0

    gemini_storage_state_path: str = "data/gemini_profile"
    gemini_app_url: str = "https://gemini.google.com/app?pli=1"
    gemini_chat_mode: str = "new_chat"
    gemini_chat_url: str | None = None
    gemini_prompt_timeout_ms: int = 5000
    gemini_response_wait_s: float = 15.0

    parser_version: str = "linkedin_v1.0"
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
    job_title_blocklist: str = ""

    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"
    user_profile_context: str = ""

    # "groq" | "chatgpt_web" | "gemini_web"
    enrichment_provider: str = "chatgpt_web"
    enrichment_web_chat_mode: str = "new_chat"
    enrichment_web_response_timeout_s: float = 45.0
    enrichment_web_max_retries: int = 1
    enrichment_web_force_new_chat: bool = True

    @property
    def parsed_title_blocklist(self) -> List[str]:
        if not self.job_title_blocklist:
            return []
        return [word.strip().lower() for word in self.job_title_blocklist.split(",") if word.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
