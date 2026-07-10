from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.web3_hot_service import (
    fetch_and_store_hot_items,
    generate_hot_content,
    get_hot_item_detail,
    hot_stats,
    list_hot_items,
    ticker_items,
)


router = APIRouter(prefix="/api/web3-hot", tags=["web3-hot"])


class FetchNowRequest(BaseModel):
    source_type: Optional[str] = None
    keyword: Optional[str] = None


class GenerateContentRequest(BaseModel):
    target_platform: str = "抖音"
    duration: str = "3分钟"
    user_instruction: str = ""
    use_llm: bool = True


@router.post("/fetch-now")
async def fetch_now(payload: Optional[FetchNowRequest] = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or FetchNowRequest()
    return await fetch_and_store_hot_items(db, source_type=payload.source_type, keyword=payload.keyword)


@router.get("/list")
def list_items(
    limit: int = Query(30, ge=1, le=200),
    heat_level: Optional[str] = None,
    trend_status: Optional[str] = None,
    keyword: Optional[str] = None,
    source_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "items": list_hot_items(
            db,
            limit=limit,
            heat_level=heat_level,
            trend_status=trend_status,
            keyword=keyword,
            source_type=source_type,
            hours=hours,
        )
    }


@router.get("/ticker")
def ticker(limit: int = Query(15, ge=1, le=50), db: Session = Depends(get_db)) -> dict:
    return {"items": ticker_items(db, limit=limit)}


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return hot_stats(db)


@router.get("/{item_id}")
def detail(item_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return get_hot_item_detail(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{item_id}/generate-content")
async def generate_content(item_id: int, payload: GenerateContentRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return await generate_hot_content(
            db,
            item_id=item_id,
            target_platform=payload.target_platform,
            duration=payload.duration,
            user_instruction=payload.user_instruction,
            use_llm=payload.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
