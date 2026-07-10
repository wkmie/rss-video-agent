from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.services.event_collectors.base import BaseEventCollector, CollectorResult, EventItem
from app.services.event_collectors.news_utils import fetch_google_news_events


class MacroCalendarCollector(BaseEventCollector):
    event_type = "macro"
    category = "宏观数据"

    async def collect(self, days: int = 30) -> CollectorResult:
        items: list[EventItem] = []
        errors: list[str] = []
        if settings.finnhub_api_key:
            finnhub_items, error = await self._fetch_finnhub(days)
            items.extend(finnhub_items)
            if error:
                errors.append(error)
        else:
            errors.append("Finnhub Economic Calendar: FINNHUB_API_KEY 未配置，已跳过 API 源")
        if not settings.trading_economics_api_key:
            errors.append("Trading Economics: TRADING_ECONOMICS_API_KEY 未配置，已跳过 API 源")

        queries = [
            '("CPI" OR "PPI" OR "FOMC" OR "Nonfarm Payrolls") ("will be released" OR "scheduled" OR "due")',
            '("Federal Reserve" OR "Powell" OR "GDP" OR "PMI") ("July" OR "August" OR "September" OR "tomorrow" OR "next week")',
        ]
        keywords = ["CPI", "PPI", "FOMC", "Federal Reserve", "Powell", "GDP", "PMI", "Nonfarm Payrolls"]
        for query in queries:
            found, error = await fetch_google_news_events(query, self.event_type, self.category, "Google News Macro", keywords, days)
            items.extend(found)
            if error:
                errors.append(error)
        return CollectorResult(items=items, errors=errors)

    async def _fetch_finnhub(self, days: int) -> tuple[list[EventItem], str | None]:
        start = datetime.now(timezone.utc).date()
        end = start + timedelta(days=days)
        url = "https://finnhub.io/api/v1/calendar/economic"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, params={"from": start.isoformat(), "to": end.isoformat(), "token": settings.finnhub_api_key})
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return [], f"Finnhub Economic Calendar: {exc}"

        events = []
        for row in data.get("economicCalendar", [])[:200]:
            name = row.get("event") or row.get("title")
            event_time_raw = row.get("time") or row.get("date")
            if not name or not event_time_raw:
                continue
            try:
                event_time = datetime.fromisoformat(str(event_time_raw).replace("Z", "+00:00"))
            except ValueError:
                event_time = datetime.fromisoformat(str(event_time_raw)).replace(tzinfo=timezone.utc)
            events.append(
                EventItem(
                    event_name=name,
                    event_type=self.event_type,
                    category=self.category,
                    event_time=event_time,
                    country=row.get("country"),
                    source="Finnhub Economic Calendar",
                    source_url=url,
                    description=row.get("unit"),
                    keywords=[name],
                    importance_level="medium",
                    expected_value=str(row.get("estimate") or "") or None,
                    previous_value=str(row.get("prev") or "") or None,
                    actual_value=str(row.get("actual") or "") or None,
                )
            )
        return events, None
