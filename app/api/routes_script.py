from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.script_service import generate_from_article, generate_from_topic


router = APIRouter(prefix="/api/script", tags=["script"])


class ScriptFromArticleRequest(BaseModel):
    article_id: int
    duration: str = "3分钟"
    platform: str = "抖音"
    use_llm: bool = True


class ScriptFromTopicRequest(BaseModel):
    topic: str = Field(min_length=2)
    duration: str = "3分钟"
    platform: str = "抖音"
    use_llm: bool = True


@router.post("/from_article")
async def from_article(payload: ScriptFromArticleRequest, db: Session = Depends(get_db)):
    try:
        return await generate_from_article(db, payload.article_id, payload.duration, payload.platform, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/from_topic")
async def from_topic(payload: ScriptFromTopicRequest, db: Session = Depends(get_db)):
    return await generate_from_topic(db, payload.topic, payload.duration, payload.platform, payload.use_llm)

