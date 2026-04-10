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

    parser_version: str = "linkedin_v1.0"

    log_level: str = "INFO"

    playwright_headless: bool = True
    playwright_timeout_ms: int = 30000
    fetch_min_delay_s: float = 2.0
    fetch_max_delay_s: float = 5.0

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "changeme"

    save_screenshot_on_fetch: bool = False

    # --- Novo: Blocklist ---
    job_title_blocklist: str = ""

    @property
    def parsed_title_blocklist(self) -> List[str]:
        if not self.job_title_blocklist:
            return []
        return [word.strip().lower() for word in self.job_title_blocklist.split(",") if word.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()