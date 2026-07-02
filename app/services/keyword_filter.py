from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Article


TIME_RANGES = {
    "最近 6 小时": timedelta(hours=6),
    "最近 12 小时": timedelta(hours=12),
    "最近 24 小时": timedelta(hours=24),
    "最近 3 天": timedelta(days=3),
    "最近 7 天": timedelta(days=7),
}

BUSINESS_CATEGORY_MAP = {
    "crypto": ["crypto_news"],
    "ai": ["ai_news", "ai_research"],
    "world_cup": ["world_cup"],
    "tech": ["tech_news"],
}


def article_query(
    db: Session,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    time_range: Optional[str] = None,
    limit: int = 50,
):
    stmt = select(Article)
    if category and category != "全部":
        categories = BUSINESS_CATEGORY_MAP.get(category, [category])
        stmt = stmt.where(Article.category.in_(categories))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Article.title.ilike(like), Article.summary.ilike(like), Article.title_zh.ilike(like)))
    if time_range and time_range in TIME_RANGES:
        since = datetime.now(timezone.utc) - TIME_RANGES[time_range]
        stmt = stmt.where(Article.published_at >= since)
    return db.scalars(stmt.order_by(Article.score.desc(), Article.published_at.desc().nullslast()).limit(limit)).all()
