from __future__ import annotations

from app.services.event_collectors.base import BaseEventCollector, CollectorResult
from app.services.event_collectors.news_utils import fetch_google_news_events


class RegulationCalendarCollector(BaseEventCollector):
    event_type = "regulation"
    category = "监管"

    async def collect(self, days: int = 30) -> CollectorResult:
        keywords = ["SEC", "CFTC", "FATF", "SFC", "MAS", "MiCA", "hearing", "ETF", "stablecoin"]
        queries = [
            '("SEC" OR "CFTC") crypto hearing ETF deadline stablecoin scheduled',
            '("MiCA" OR "FATF" OR "SFC" OR "MAS") crypto regulation deadline meeting',
        ]
        items = []
        errors = []
        for query in queries:
            found, error = await fetch_google_news_events(query, self.event_type, self.category, "Google News Regulation", keywords, days)
            items.extend(found)
            if error:
                errors.append(error)
        return CollectorResult(items=items, errors=errors)
