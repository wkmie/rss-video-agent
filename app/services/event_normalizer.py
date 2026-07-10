from __future__ import annotations

import hashlib
import re
from datetime import datetime, time, timezone
from typing import Optional

from app.services.event_collectors.base import EventItem


IMPORTANCE_BY_SCORE = [
    (90, "critical"),
    (70, "high"),
    (40, "medium"),
    (0, "low"),
]


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def default_day_time(value: datetime) -> datetime:
    if value.hour == 0 and value.minute == 0 and value.second == 0:
        return datetime.combine(value.date(), time(hour=9), tzinfo=value.tzinfo or timezone.utc)
    return value


def content_hash(*parts: str) -> str:
    raw = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def score_to_importance(score: Optional[float]) -> str:
    if score is None:
        return "medium"
    for minimum, label in IMPORTANCE_BY_SCORE:
        if score >= minimum:
            return label
    return "low"


def infer_impact_score(event_type: str, text: str, fallback: float = 55) -> float:
    lowered = text.lower()
    high_patterns = {
        "macro": [("fomc", 95), ("cpi", 92), ("nonfarm", 90), ("payroll", 90), ("federal reserve", 88), ("powell", 84)],
        "crypto": [("etf", 90), ("mainnet", 82), ("exchange listing", 82), ("stablecoin", 80), ("airdrop", 72), ("governance", 68)],
        "token_unlock": [("cliff", 80), ("unlock", 72), ("vesting", 60)],
        "ai_tech": [("openai", 90), ("nvidia", 86), ("apple", 84), ("google", 82), ("microsoft", 82), ("anthropic", 82)],
        "regulation": [("sec", 88), ("hearing", 84), ("stablecoin", 84), ("etf", 88), ("cftc", 78), ("mica", 78)],
        "security": [("zero-day", 95), ("0-day", 95), ("critical", 88), ("cve", 78), ("patch tuesday", 78), ("ransomware", 82)],
    }
    for pattern, score in high_patterns.get(event_type, []):
        if pattern in lowered:
            return float(score)
    return fallback


def normalize_keywords(keywords: list[str], text: str) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        clean = keyword.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            normalized.append(clean)
    for token in re.findall(r"\b[A-Z][A-Za-z0-9.+-]{1,12}\b", text):
        if token.lower() not in seen and len(normalized) < 10:
            seen.add(token.lower())
            normalized.append(token)
    return normalized[:12]


class EventNormalizer:
    def normalize(self, item: EventItem) -> tuple[EventItem, str]:
        event_time = ensure_utc(default_day_time(item.event_time))
        text = f"{item.event_name} {item.description or ''}"
        score = item.impact_score if item.impact_score is not None else infer_impact_score(item.event_type, text)
        inferred_importance = score_to_importance(score)
        importance = inferred_importance if item.importance_level in {"low", "medium"} else item.importance_level
        if not item.source_url and importance in {"high", "critical"}:
            importance = "medium"
        normalized = item.model_copy(
            update={
                "event_time": event_time,
                "impact_score": score,
                "importance_level": importance,
                "keywords": normalize_keywords(item.keywords, text),
            }
        )
        digest = content_hash(normalized.event_name, normalized.event_time.isoformat(), normalized.source)
        return normalized, digest
