from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventItem(BaseModel):
    event_name: str
    event_type: str
    category: str
    event_time: datetime
    country: Optional[str] = None
    asset_or_topic: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    description: Optional[str] = None
    keywords: list[str] = []
    importance_level: str = "medium"
    expected_value: Optional[str] = None
    previous_value: Optional[str] = None
    actual_value: Optional[str] = None
    impact_score: Optional[float] = None


class CollectorResult(BaseModel):
    items: list[EventItem] = []
    errors: list[str] = []


class BaseEventCollector:
    event_type = "other"
    category = "其他"

    async def collect(self, days: int = 30) -> CollectorResult:
        raise NotImplementedError
