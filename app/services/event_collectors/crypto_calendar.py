from __future__ import annotations

from app.config import settings
from app.services.event_collectors.base import BaseEventCollector, CollectorResult
from app.services.event_collectors.news_utils import fetch_google_news_events


class CryptoCalendarCollector(BaseEventCollector):
    event_type = "crypto"
    category = "Web3"

    async def collect(self, days: int = 30) -> CollectorResult:
        errors: list[str] = []
        if not settings.coinmarketcal_api_key:
            errors.append("CoinMarketCal: COINMARKETCAL_API_KEY 未配置，已使用新闻 RSS 兜底")
        keywords = ["mainnet", "airdrop", "snapshot", "listing", "ETF", "governance", "upgrade", "stablecoin"]
        queries = [
            'crypto (mainnet OR airdrop OR snapshot OR listing OR upgrade) ("July" OR "August" OR "tomorrow" OR "next week")',
            'Bitcoin ETF OR Ethereum ETF approval deadline hearing scheduled',
        ]
        items = []
        for query in queries:
            found, error = await fetch_google_news_events(query, self.event_type, self.category, "Google News Web3", keywords, days)
            items.extend(found)
            if error:
                errors.append(error)
        return CollectorResult(items=items, errors=errors)
