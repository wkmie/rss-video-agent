from __future__ import annotations

from app.services.event_collectors.base import BaseEventCollector, CollectorResult
from app.services.event_collectors.news_utils import fetch_google_news_events


class TechCalendarCollector(BaseEventCollector):
    event_type = "ai_tech"
    category = "AI科技"

    async def collect(self, days: int = 30) -> CollectorResult:
        keywords = ["OpenAI", "Apple", "Google", "Nvidia", "Meta", "Microsoft", "Anthropic", "AI chip"]
        queries = [
            '("OpenAI" OR "Anthropic" OR "Google I/O" OR "Microsoft Build") ("event" OR "launch" OR "scheduled")',
            '("Nvidia earnings" OR "Apple Event" OR "Meta Connect") ("July" OR "August" OR "tomorrow" OR "next week")',
        ]
        items = []
        errors = []
        for query in queries:
            found, error = await fetch_google_news_events(query, self.event_type, self.category, "Google News AI Tech", keywords, days)
            items.extend(found)
            if error:
                errors.append(error)
        return CollectorResult(items=items, errors=errors)
