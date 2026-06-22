from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import feedparser
import httpx

from app.config import BASE_DIR, settings
from app.rss.cleaner import normalize_summary, normalize_title, parse_datetime
from app.rss.models import RssArticle, RssSource
from app.utils.text import content_hash


def load_sources(path: Optional[Path] = None) -> list[RssSource]:
    source_path = path or BASE_DIR / "config" / "rss_sources.json"
    data = json.loads(source_path.read_text(encoding="utf-8"))
    return [RssSource(**item) for item in data.get("rss_sources", []) if item.get("enabled", True)]


async def fetch_source(source: RssSource, limit: Optional[int] = None) -> list[RssArticle]:
    max_items = limit or settings.rss_max_articles_per_source
    headers = {"User-Agent": "rss-video-agent/0.1"}
    async with httpx.AsyncClient(timeout=settings.rss_timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = await client.get(str(source.url))
        response.raise_for_status()
    feed = feedparser.parse(response.content)
    articles: list[RssArticle] = []
    for entry in feed.entries[:max_items]:
        title = normalize_title(getattr(entry, "title", ""))
        link = str(getattr(entry, "link", "") or "")
        summary = normalize_summary(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        published = parse_datetime(
            getattr(entry, "published", None)
            or getattr(entry, "updated", None)
            or getattr(entry, "published_parsed", None)
            or getattr(entry, "updated_parsed", None)
        )
        articles.append(
            RssArticle(
                source_name=source.name,
                source_url=str(source.url),
                title=title,
                link=link,
                summary=summary,
                published_at=published,
                category=source.category,
                language=source.language,
                content_hash=content_hash(link, title, source.name),
            )
        )
    return articles


async def fetch_all_sources() -> tuple[list[RssArticle], list[str]]:
    articles: list[RssArticle] = []
    errors: list[str] = []
    for source in load_sources():
        try:
            articles.extend(await fetch_source(source))
        except Exception as exc:
            errors.append(f"{source.name}: {exc}")
    return articles, errors
