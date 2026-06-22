from __future__ import annotations

import hashlib
import re
from html import unescape
from typing import Optional


def clean_html(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def content_hash(*parts: Optional[str]) -> str:
    raw = "|".join(part or "" for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compact(text: Optional[str], limit: int = 240) -> str:
    value = clean_html(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
