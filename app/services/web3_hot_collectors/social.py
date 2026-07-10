from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.services.web3_hot_collectors.base import BaseHotFeedCollector, HotCollectorResult, HotFeedItem


class XRecentSearchCollector(BaseHotFeedCollector):
    QUERY = '(BTC OR Bitcoin OR ETH OR Ethereum OR ETF OR MicroStrategy OR Strategy OR hack OR depeg OR Binance OR Coinbase) lang:en -is:retweet'

    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        if source_type and source_type != "x_recent_search":
            return result
        source = next((item for item in self.sources if item.get("type") == "x_recent_search"), None)
        if not source or not source.get("enabled", False):
            return result
        if not settings.x_bearer_token:
            result.errors.append("X API 未配置，已跳过 X Recent Search")
            return result

        query = keyword or self.QUERY
        headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
        params = {
            "query": query,
            "max_results": min(self.max_items_per_source, 100),
            "tweet.fields": "created_at,public_metrics,author_id,lang",
        }
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                response = await client.get("https://api.x.com/2/tweets/search/recent", params=params)
                response.raise_for_status()
            data = response.json()
            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                created_at = None
                if tweet.get("created_at"):
                    created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                result.items.append(
                    HotFeedItem(
                        source_name=source.get("name", "X Crypto Search"),
                        source_type="x_recent_search",
                        source_priority=source.get("priority", "P1"),
                        title=tweet.get("text", "")[:240],
                        content=tweet.get("text", ""),
                        summary=tweet.get("text", "")[:280],
                        link=f"https://x.com/i/web/status/{tweet.get('id')}",
                        author=tweet.get("author_id"),
                        published_at=created_at,
                        language=tweet.get("lang"),
                        raw_metrics={
                            "likes": metrics.get("like_count", 0),
                            "reposts": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "quotes": metrics.get("quote_count", 0),
                        },
                        raw_json=tweet,
                    )
                )
        except Exception as exc:
            result.errors.append(f"X Crypto Search: {exc}")
        return result


class LunarCrushCollector(BaseHotFeedCollector):
    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        if source_type and source_type != "lunarcrush":
            return result
        source = next((item for item in self.sources if item.get("type") == "lunarcrush"), None)
        if not source or not source.get("enabled", False):
            return result
        if not settings.lunarcrush_api_key:
            result.errors.append("LunarCrush API 未配置，已跳过社交热度源")
            return result

        headers = {"Authorization": f"Bearer {settings.lunarcrush_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                response = await client.get("https://lunarcrush.com/api4/public/coins/list/v2")
                response.raise_for_status()
            data: dict[str, Any] = response.json()
            assets = data.get("data", [])[: self.max_items_per_source]
            for asset in assets:
                symbol = asset.get("symbol") or asset.get("s")
                name = asset.get("name") or asset.get("n") or symbol
                if keyword and keyword.lower() not in f"{symbol} {name}".lower():
                    continue
                social_score = asset.get("galaxy_score") or asset.get("social_score") or asset.get("alt_rank") or 0
                result.items.append(
                    HotFeedItem(
                        source_name=source.get("name", "LunarCrush"),
                        source_type="lunarcrush",
                        source_priority=source.get("priority", "P1"),
                        title=f"{symbol} social heat is rising" if symbol else f"{name} social heat is rising",
                        content=f"LunarCrush social heat signal for {name}.",
                        summary=f"{name} appears in LunarCrush social ranking.",
                        link=None,
                        author=None,
                        published_at=datetime.now(timezone.utc),
                        language="en",
                        raw_metrics={"social_score": social_score, "source_rank": asset.get("rank")},
                        raw_json=asset,
                    )
                )
        except Exception as exc:
            result.errors.append(f"LunarCrush: {exc}")
        return result
