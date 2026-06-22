from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.news_service import analyze_article, fetch_and_store, list_articles, top_topic_pool


router = APIRouter(prefix="/api/news", tags=["news"])


class AnalyzeRequest(BaseModel):
    article_id: int
    use_llm: bool = True


@router.post("/fetch")
async def fetch_news(db: Session = Depends(get_db)):
    return await fetch_and_store(db)


@router.get("/list")
def get_news(
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    time_range: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return {"items": list_articles(db, category=category, keyword=keyword, time_range=time_range, limit=limit)}


@router.get("/topics")
def get_topics(
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    time_range: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return {"items": top_topic_pool(db, category, keyword, time_range, limit)}


@router.post("/analyze")
async def analyze_news(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        return await analyze_article(db, payload.article_id, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
