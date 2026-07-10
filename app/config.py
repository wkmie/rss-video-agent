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
    trading_economics_api_key: str = ""
    finnhub_api_key: str = ""
    coinmarketcal_api_key: str = ""
    token_unlocks_api_key: str = ""
    messari_api_key: str = ""
    pre_event_fetch_days: int = 30
    pre_event_default_countries: str = "United States,China,Japan,Euro Area"
    pre_event_min_importance: str = "medium"
    web3_hot_feed_enabled: bool = True
    web3_hot_refresh_seconds: int = 60
    web3_hot_item_ttl_hours: int = 24
    web3_hot_max_items_per_source: int = 50
    x_bearer_token: str = ""
    lunarcrush_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
