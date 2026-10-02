from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Agentic AI Payment Assistant"
    database_url: str = f"sqlite+aiosqlite:///{ROOT_DIR / 'data' / 'demo.sqlite3'}"
    secret_key: str = "change-me-for-demo"
    llm_provider: str = "openai-compatible"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    frontend_dir: str = str(ROOT_DIR / "frontend")
    approval_threshold: float = 10000
    rate_limit_per_minute: int = 40

    model_config = SettingsConfigDict(env_file=ROOT_DIR / "backend" / ".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
