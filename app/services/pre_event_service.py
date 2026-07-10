from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventCalendar
from app.services.event_collectors import COLLECTORS
from app.services.event_normalizer import EventNormalizer


STATUS_LABELS = {
    "待生成": "pending",
    "已生成": "topic_generated",
    "已审核": "reviewed",
    "已发布": "published",
    "已放弃": "abandoned",
}

IMPORTANCE_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def event_to_dict(event: EventCalendar) -> dict:
    return {
        "id": event.id,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "category": event.category,
        "event_time": event.event_time.isoformat() if event.event_time else None,
        "country": event.country,
        "asset_or_topic": event.asset_or_topic,
        "source": event.source,
        "source_url": event.source_url,
        "description": event.description,
        "keywords": json.loads(event.keywords or "[]"),
        "importance_level": event.importance_level,
        "expected_value": event.expected_value,
        "previous_value": event.previous_value,
        "actual_value": event.actual_value,
        "impact_score": event.impact_score,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
    }


async def fetch_and_store_pre_events(
    db: Session,
    days: int = 30,
    categories: Optional[list[str]] = None,
    force_refresh: bool = False,
) -> dict:
    normalizer = EventNormalizer()
    fetched_count = 0
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    errors: list[str] = []

    selected = categories or list(COLLECTORS.keys())
    for category in selected:
        collector_cls = COLLECTORS.get(category)
        if not collector_cls:
            errors.append(f"未知分类：{category}")
            continue
        result = await collector_cls().collect(days=days)
        errors.extend(result.errors)
        for item in result.items:
            fetched_count += 1
            normalized, digest = normalizer.normalize(item)
            existing = db.scalar(select(EventCalendar).where(EventCalendar.content_hash == digest))
            if existing and not force_refresh:
                skipped_count += 1
                continue
            if existing:
                event = existing
                updated_count += 1
            else:
                event = EventCalendar(content_hash=digest)
                db.add(event)
                inserted_count += 1
            event.event_name = normalized.event_name
            event.event_type = normalized.event_type
            event.category = normalized.category
            event.event_time = normalized.event_time
            event.country = normalized.country
            event.asset_or_topic = normalized.asset_or_topic
            event.source = normalized.source
            event.source_url = normalized.source_url
            event.description = normalized.description
            event.keywords = json.dumps(normalized.keywords, ensure_ascii=False)
            event.importance_level = normalized.importance_level
            event.expected_value = normalized.expected_value
            event.previous_value = normalized.previous_value
            event.actual_value = normalized.actual_value
            event.impact_score = normalized.impact_score
            event.status = event.status or "pending"
            event.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "fetched_count": fetched_count,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


def list_pre_events(
    db: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    importance_level: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    stmt = select(EventCalendar)
    if start_time:
        stmt = stmt.where(EventCalendar.event_time >= start_time)
    if end_time:
        stmt = stmt.where(EventCalendar.event_time <= end_time)
    if category and category != "全部":
        stmt = stmt.where(EventCalendar.category == category)
    if event_type:
        stmt = stmt.where(EventCalendar.event_type == event_type)
    if importance_level and importance_level != "全部":
        stmt = stmt.where(EventCalendar.importance_level == importance_level)
    if status and status != "全部":
        stmt = stmt.where(EventCalendar.status == STATUS_LABELS.get(status, status))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            EventCalendar.event_name.ilike(like)
            | EventCalendar.description.ilike(like)
            | EventCalendar.keywords.ilike(like)
            | EventCalendar.asset_or_topic.ilike(like)
        )
    stmt = stmt.order_by(EventCalendar.impact_score.desc().nullslast(), EventCalendar.event_time.asc()).limit(limit)
    return [event_to_dict(event) for event in db.scalars(stmt).all()]


def upcoming_events(
    db: Session,
    days: int = 7,
    category: Optional[str] = None,
    importance_level: Optional[str] = None,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    return list_pre_events(
        db,
        start_time=now,
        end_time=now + timedelta(days=days),
        category=category,
        importance_level=importance_level,
    )


def update_event_status(db: Session, event_id: int, status: str) -> dict:
    event = db.get(EventCalendar, event_id)
    if not event:
        raise ValueError("Event not found")
    event.status = STATUS_LABELS.get(status, status)
    event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event_to_dict(event)
