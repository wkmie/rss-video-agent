from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.trading_cognition.service import generate_trading_cognition


router = APIRouter(prefix="/api/trading-cognition", tags=["trading-cognition"])


class TradingCognitionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    duration: str = "3分钟"
    platform: str = "抖音"
    use_llm: bool = True
    knowledge_limit: int = Field(default=4, ge=1, le=6)


@router.post("/generate")
async def generate(payload: TradingCognitionRequest, db: Session = Depends(get_db)):
    try:
        return await generate_trading_cognition(
            db=db,
            question=payload.question,
            duration=payload.duration,
            platform=payload.platform,
            use_llm=payload.use_llm,
            knowledge_limit=payload.knowledge_limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
