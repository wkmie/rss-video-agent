from __future__ import annotations

from app.config import settings
from app.services.event_collectors.base import BaseEventCollector, CollectorResult
from app.services.event_collectors.news_utils import fetch_google_news_events


class TokenUnlockCollector(BaseEventCollector):
    event_type = "token_unlock"
    category = "Token解锁"

    async def collect(self, days: int = 30) -> CollectorResult:
        errors: list[str] = []
        if not settings.token_unlocks_api_key and not settings.messari_api_key:
            errors.append("Token Unlocks/Messari: TOKEN_UNLOCKS_API_KEY 或 MESSARI_API_KEY 未配置，已使用新闻 RSS 兜底")
        keywords = ["unlock", "vesting", "cliff unlock", "linear unlock", "circulating supply"]
        items, error = await fetch_google_news_events(
            'token unlock vesting cliff unlock ("July" OR "August" OR "tomorrow" OR "next week")',
            self.event_type,
            self.category,
            "Google News Token Unlocks",
            keywords,
            days,
        )
        if error:
            errors.append(error)
        return CollectorResult(items=items, errors=errors)
