from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    database_url: str = "sqlite:///./rss_video_agent.db"
    rss_max_articles_per_source: int = 10
    rss_timeout_seconds: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
