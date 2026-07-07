from __future__ import annotations

import asyncio
import json as jsonlib
import json
import re
from html import unescape
from pathlib import Path
from typing import Optional

import feedparser
import httpx

from app.config import BASE_DIR, settings
from app.rss.cleaner import normalize_summary, normalize_title, parse_datetime
from app.rss.models import RssArticle, RssSource
from app.utils.text import content_hash


PRAGMALENS_CATEGORY_MAP = {
    "crypto": "crypto_news",
    "ai": "ai_news",
    "finance": "tech_news",
    "poker": "tech_news",
    "polymarket": "prediction_market",
}


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
    if not feed.entries and "pragmalens.xyz" in str(source.url):
        return parse_pragmalens_page(response.text, source, max_items)
    if not feed.entries and "odaily.news" in str(source.url):
        return parse_odaily_page(response.text, source, max_items)
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


def decode_js_string(value: str) -> str:
    try:
        return jsonlib.loads(f'"{value}"')
    except jsonlib.JSONDecodeError:
        return value.replace(r"\/", "/").replace(r"\n", "\n")


def parse_pragmalens_page(html: str, source: RssSource, max_items: int) -> list[RssArticle]:
    pattern = re.compile(
        r'\{\\"id\\":(?P<id>\d+),\\"title\\":\\"(?P<title>(?:\\\\.|[^"\\])*)\\",'
        r'\\"body\\":\\"(?P<body>(?:\\\\.|[^"\\])*)\\",\\"category\\":\\"(?P<category>[^"\\]*)\\"'
        r'.*?\\"source_url\\":\\"(?P<link>(?:\\\\.|[^"\\])*)\\"'
        r'.*?\\"published_at\\":\\"(?P<published>(?:\\\\.|[^"\\])*)\\"',
        re.DOTALL,
    )
    articles: list[RssArticle] = []
    seen_links: set[str] = set()
    for match in pattern.finditer(html):
        title = normalize_title(decode_js_string(match.group("title")))
        link = decode_js_string(match.group("link"))
        if not title or not link or link in seen_links:
            continue
        seen_links.add(link)
        category = PRAGMALENS_CATEGORY_MAP.get(match.group("category").lower(), source.category)
        summary = normalize_summary(decode_js_string(match.group("body")))
        published = parse_datetime(decode_js_string(match.group("published")))
        articles.append(
            RssArticle(
                source_name=source.name,
                source_url=str(source.url),
                title=title,
                link=link,
                summary=summary,
                published_at=published,
                category=category,
                language=source.language,
                content_hash=content_hash(link, title, source.name),
            )
        )
        if len(articles) >= max_items:
            break
    return articles


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(value)).strip()


def parse_odaily_page(html: str, source: RssSource, max_items: int) -> list[RssArticle]:
    pattern = re.compile(
        r'\{\\"id\\":(?P<id>\d+),\\"entityType\\":(?P<entity_type>\d+),\\"entityId\\":(?P<entity_id>\d+)'
        r'.*?\\"publishedTime\\":\\"(?P<published>(?:\\\\.|[^"\\])*)\\"'
        r'.*?\\"newsUrl\\":(?P<news_url>null|\\"(?:\\\\.|[^"\\])*\\")'
        r'.*?\\"summary\\":\\"(?P<summary>(?:\\\\.|[^"\\])*)\\"'
        r'.*?\\"title\\":\\"(?P<title>(?:\\\\.|[^"\\])*)\\"',
        re.DOTALL,
    )
    articles: list[RssArticle] = []
    seen_links: set[str] = set()
    for match in pattern.finditer(html):
        title = normalize_title(decode_js_string(match.group("title")))
        if not title:
            continue
        entity_type = match.group("entity_type")
        entity_id = match.group("entity_id")
        news_url = match.group("news_url")
        if news_url != "null":
            link = decode_js_string(news_url[2:-2])
        elif entity_type == "4":
            link = f"https://www.odaily.news/zh-CN/newsflash/{entity_id}"
        else:
            link = f"https://www.odaily.news/zh-CN/post/{entity_id}"
        if link in seen_links:
            continue
        seen_links.add(link)
        summary = strip_html(decode_js_string(match.group("summary")))
        published = parse_datetime(decode_js_string(match.group("published")))
        articles.append(
            RssArticle(
                source_name=source.name,
                source_url=str(source.url),
                title=title,
                link=link,
                summary=normalize_summary(summary),
                published_at=published,
                category=source.category,
                language=source.language,
                content_hash=content_hash(link, title, source.name),
            )
        )
        if len(articles) >= max_items:
            break
    return articles


async def fetch_all_sources() -> tuple[list[RssArticle], list[str]]:
    articles: list[RssArticle] = []
    errors: list[str] = []
    semaphore = asyncio.Semaphore(6)

    async def fetch_with_error(source: RssSource) -> tuple[list[RssArticle], Optional[str]]:
        async with semaphore:
            try:
                return await fetch_source(source), None
            except Exception as exc:
                detail = str(exc) or exc.__class__.__name__
                return [], f"{source.name}: {detail}"

    sources = load_sources()
    results = await asyncio.gather(*(fetch_with_error(source) for source in sources))
    for source_articles, error in results:
        articles.extend(source_articles)
        if error:
            errors.append(error)
    return articles, errors
