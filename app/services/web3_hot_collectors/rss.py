from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from app.config import settings
from app.services.web3_hot_collectors.base import BaseHotFeedCollector, HotCollectorResult, HotFeedItem


def parse_entry_date(entry: Any) -> datetime | None:
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def guess_language(text: str) -> str:
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return "zh"
    return "en"


class RSSHotFeedCollector(BaseHotFeedCollector):
    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        source_types = {"rss", "google_news_rss"}
        if source_type and source_type not in source_types:
            return result

        async with httpx.AsyncClient(timeout=settings.rss_timeout_seconds, follow_redirects=True) as client:
            for source in self.sources:
                if not source.get("enabled", True) or source.get("type") not in source_types:
                    continue
                if source_type and source.get("type") != source_type:
                    continue
                try:
                    response = await client.get(source["url"])
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                    entries = feed.entries[: self.max_items_per_source]
                    for entry in entries:
                        title = (getattr(entry, "title", "") or "").strip()
                        link = (getattr(entry, "link", "") or "").strip()
                        summary = (getattr(entry, "summary", "") or getattr(entry, "description", "") or "").strip()
                        if not title or (keyword and keyword.lower() not in f"{title} {summary}".lower()):
                            continue
                        result.items.append(
                            HotFeedItem(
                                source_name=source["name"],
                                source_type=source["type"],
                                source_priority=source.get("priority", "P2"),
                                title=title,
                                content=summary,
                                summary=summary,
                                link=link,
                                author=(getattr(entry, "author", "") or "").strip() or None,
                                published_at=parse_entry_date(entry),
                                language=guess_language(f"{title} {summary}"),
                                raw_metrics={"source_rank": source.get("priority", "P2")},
                                raw_json=dict(entry),
                            )
                        )
                except Exception as exc:
                    result.errors.append(f"{source.get('name', 'unknown')}: {exc}")
        return result
