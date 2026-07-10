from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import EventCalendar
from app.services.pre_event_service import fetch_and_store_pre_events, list_pre_events, upcoming_events, update_event_status
from app.services.pre_topic_service import generate_pre_topic, list_pre_topics, update_pre_topic_status


router = APIRouter(tags=["pre_event_topics"])


class FetchPreEventsRequest(BaseModel):
    days: int = 30
    categories: Optional[list[str]] = None
    force_refresh: bool = False


class GeneratePreTopicRequest(BaseModel):
    event_id: int
    target_platform: str = "视频号"
    duration: str = "3分钟"
    user_instruction: str = ""
    use_llm: bool = True


class StatusUpdateRequest(BaseModel):
    status: str


@router.post("/api/pre-events/fetch")
async def fetch_pre_events(payload: FetchPreEventsRequest, db: Session = Depends(get_db)):
    return await fetch_and_store_pre_events(db, payload.days, payload.categories, payload.force_refresh)


@router.get("/api/pre-events/list")
def pre_events_list(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    importance_level: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return {
        "items": list_pre_events(
            db,
            start_time=start_time,
            end_time=end_time,
            category=category,
            event_type=event_type,
            importance_level=importance_level,
            status=status,
            keyword=keyword,
            limit=limit,
        )
    }


@router.get("/api/pre-events/upcoming")
def pre_events_upcoming(
    days: int = 7,
    category: Optional[str] = None,
    importance_level: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return {"items": upcoming_events(db, days, category, importance_level)}


@router.post("/api/pre-topics/generate")
async def pre_topics_generate(payload: GeneratePreTopicRequest, db: Session = Depends(get_db)):
    try:
        return await generate_pre_topic(
            db,
            payload.event_id,
            payload.target_platform,
            payload.duration,
            payload.user_instruction,
            payload.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/pre-topics/list")
def pre_topics_list(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    return {"items": list_pre_topics(db, status, limit)}


@router.put("/api/pre-topics/{topic_id}/status")
def pre_topic_status(topic_id: int, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    try:
        return update_pre_topic_status(db, topic_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/pre-events/{event_id}/refresh")
async def pre_event_refresh(event_id: int, db: Session = Depends(get_db)):
    event = db.get(EventCalendar, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return await fetch_and_store_pre_events(db, 30, [event.category], force_refresh=True)


@router.put("/api/pre-events/{event_id}/status")
def pre_event_status(event_id: int, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    try:
        return update_event_status(db, event_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
