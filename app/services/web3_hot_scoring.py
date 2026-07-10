from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Web3HotItem, Web3HotScore


SOURCE_WEIGHTS = {"P0": 20.0, "P1": 16.0, "P2": 11.0, "P3": 7.0}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_dt(dt: datetime | None) -> datetime:
    if dt is None:
        return utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def tokenize_title(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]{3,}|[\u4e00-\u9fff]{2,}", title.lower())
    stop = {"the", "and", "for", "with", "from", "this", "that", "crypto", "bitcoin"}
    return {word for word in words if word not in stop}


def similar_title_count(db: Session, item: Web3HotItem, hours: int = 6) -> int:
    tokens = tokenize_title(item.title)
    if not tokens:
        return 1
    window_start = utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(Web3HotItem.id, Web3HotItem.title, Web3HotItem.source_name)
        .where(Web3HotItem.fetched_at >= window_start)
        .where(Web3HotItem.id != item.id)
        .limit(300)
    ).all()
    matched_sources = {item.source_name}
    for _, title, source in rows:
        other_tokens = tokenize_title(title or "")
        if not other_tokens:
            continue
        overlap = len(tokens & other_tokens) / max(len(tokens), 1)
        if overlap >= 0.45:
            matched_sources.add(source)
    return len(matched_sources)


def compute_scores(db: Session, item: Web3HotItem, keywords_config: dict[str, Any], previous_score: float | None = None) -> dict[str, Any]:
    now = utcnow()
    published_at = normalize_dt(item.published_at or item.fetched_at)
    age_hours = max((now - published_at).total_seconds() / 3600, 0)
    if age_hours <= 1:
        recency_score = 20.0
    elif age_hours <= 24:
        recency_score = max(4.0, 20.0 - (age_hours - 1) * 16.0 / 23.0)
    else:
        recency_score = 2.0

    try:
        metrics = json.loads(item.raw_metrics_json or "{}")
    except json.JSONDecodeError:
        metrics = {}
    interactions = (
        float(metrics.get("likes", 0) or 0)
        + float(metrics.get("reposts", 0) or 0) * 2
        + float(metrics.get("replies", 0) or 0) * 1.5
        + float(metrics.get("comments", 0) or 0)
        + float(metrics.get("shares", 0) or 0) * 2
        + float(metrics.get("views", 0) or 0) * 0.01
        + float(metrics.get("social_score", 0) or 0)
    )
    if interactions > 0:
        engagement_score = min(25.0, 5.0 + math.log10(interactions + 1) * 7.0)
    else:
        duplicate_sources = similar_title_count(db, item)
        engagement_score = min(25.0, 7.0 + duplicate_sources * 3.0)

    source_weight_score = SOURCE_WEIGHTS.get(item.source_priority, 8.0)
    text = f"{item.title} {item.summary or ''} {item.content or ''}".lower()
    matched_keywords = load_json_list(item.matched_keywords_json)
    risk_keywords = [kw for kw in keywords_config.get("risk_keywords", []) if kw.lower() in text]
    keyword_score = min(15.0, 4.0 + len(matched_keywords) * 2.0)
    duplicate_sources = similar_title_count(db, item)
    velocity_score = min(10.0, max(0.0, (duplicate_sources - 1) * 3.5))
    risk_score = min(10.0, len(risk_keywords) * 4.0)
    confidence_score = min(10.0, 4.0 + duplicate_sources * 2.0 + (2.0 if item.source_type in {"rss", "google_news_rss"} else 0.0))

    heat_score = min(
        100.0,
        recency_score + engagement_score + source_weight_score + keyword_score + velocity_score + risk_score,
    )
    major_risk = risk_score >= 8.0 and item.source_type != "x_recent_search"
    if heat_score >= 85 or major_risk:
        heat_level = "red"
    elif heat_score >= 65:
        heat_level = "yellow"
    else:
        heat_level = "gray"

    is_recent = age_hours <= 2
    if previous_score is None and is_recent:
        trend_status = "new"
    elif previous_score is not None and heat_score - previous_score >= 8:
        trend_status = "rising"
    elif heat_score >= 75:
        trend_status = "hot"
    else:
        trend_status = "cooling" if previous_score is not None and previous_score - heat_score >= 8 else "new"

    detail = {
        "recency_score": round(recency_score, 2),
        "engagement_score": round(engagement_score, 2),
        "source_weight_score": round(source_weight_score, 2),
        "keyword_score": round(keyword_score, 2),
        "velocity_score": round(velocity_score, 2),
        "risk_score": round(risk_score, 2),
        "confidence_score": round(confidence_score, 2),
        "duplicate_source_count": duplicate_sources,
        "risk_keywords": risk_keywords,
    }
    return {
        "heat_score": round(heat_score, 2),
        "recency_score": round(recency_score, 2),
        "engagement_score": round(engagement_score, 2),
        "source_weight_score": round(source_weight_score, 2),
        "keyword_score": round(keyword_score, 2),
        "velocity_score": round(velocity_score, 2),
        "risk_score": round(risk_score, 2),
        "confidence_score": round(confidence_score, 2),
        "heat_level": heat_level,
        "trend_status": trend_status,
        "score_detail_json": json.dumps(detail, ensure_ascii=False),
    }
