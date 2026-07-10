from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class HotFeedItem:
    source_name: str
    source_type: str
    source_priority: str
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    link: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    language: Optional[str] = None
    raw_metrics: dict[str, Any] = field(default_factory=dict)
    raw_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class HotCollectorResult:
    items: list[HotFeedItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BaseHotFeedCollector:
    def __init__(self, sources: list[dict[str, Any]], max_items_per_source: int) -> None:
        self.sources = sources
        self.max_items_per_source = max_items_per_source

    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        raise NotImplementedError
