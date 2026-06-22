from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from dateutil import parser

from app.utils.text import clean_html


def parse_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, str):
            dt = parser.parse(value)
        else:
            dt = datetime(*value[:6])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_title(title: Optional[str]) -> str:
    return clean_html(title) or "Untitled"


def normalize_summary(summary: Optional[str]) -> str:
    return clean_html(summary)
