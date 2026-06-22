from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class RssSource(BaseModel):
    name: str
    url: HttpUrl
    language: str = "en"
    category: str
    enabled: bool = True


class RssArticle(BaseModel):
    source_name: str
    source_url: str
    title: str
    link: str
    summary: str = ""
    published_at: Optional[datetime] = None
    category: str
    language: str = "en"
    content_hash: str
