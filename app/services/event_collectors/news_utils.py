from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from app.services.event_collectors.base import EventItem


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def google_news_rss_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"


def parse_future_date(text: str, days: int) -> datetime | None:
    now = datetime.now(timezone.utc)
    lowered = text.lower()
    if "tomorrow" in lowered:
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    if "next week" in lowered:
        return (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)

    iso_match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        candidate = datetime(year, month, day, 9, tzinfo=timezone.utc)
        return candidate if now <= candidate <= now + timedelta(days=days) else None

    month_match = re.search(
        r"\b("
        + "|".join(MONTHS)
        + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*(20\d{2}))?",
        lowered,
    )
    if month_match:
        month = MONTHS[month_match.group(1)]
        day = int(month_match.group(2))
        year = int(month_match.group(3) or now.year)
        candidate = datetime(year, month, day, 9, tzinfo=timezone.utc)
        if candidate < now:
            candidate = candidate.replace(year=year + 1)
        return candidate if now <= candidate <= now + timedelta(days=days) else None
    return None


async def fetch_google_news_events(
    query: str,
    event_type: str,
    category: str,
    source: str,
    keywords: list[str],
    days: int,
    limit: int = 8,
) -> tuple[list[EventItem], str | None]:
    url = google_news_rss_url(query)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": "rss-video-agent/0.1"}) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception as exc:
        return [], f"{source}: {exc}"

    feed = feedparser.parse(response.content)
    items: list[EventItem] = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "").strip()
        link = getattr(entry, "link", "") or url
        event_time = parse_future_date(f"{title} {summary}", days)
        if not title or not event_time:
            continue
        text = f"{title} {summary}"
        matched_keywords = [keyword for keyword in keywords if keyword.lower() in text.lower()]
        items.append(
            EventItem(
                event_name=title,
                event_type=event_type,
                category=category,
                event_time=event_time,
                asset_or_topic=matched_keywords[0] if matched_keywords else None,
                source=source,
                source_url=link,
                description=summary or "从新闻 RSS 中识别到的未来事件，具体时间和细节需二次确认。",
                keywords=matched_keywords or keywords[:3],
                importance_level="medium",
            )
        )
    return items, None
