from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api.auth_dependencies import require_current_user
from app.api.routes_auth import router as auth_router
from app.api.routes_news import router as news_router
from app.api.routes_pre_topics import router as pre_topics_router
from app.api.routes_script import router as script_router
from app.api.routes_trading_cognition import router as trading_cognition_router
from app.api.routes_web3_hot import router as web3_hot_router
from app.db.database import init_db


app = FastAPI(title="RSS Video Agent", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(news_router, dependencies=[Depends(require_current_user)])
app.include_router(script_router, dependencies=[Depends(require_current_user)])
app.include_router(trading_cognition_router, dependencies=[Depends(require_current_user)])
app.include_router(pre_topics_router, dependencies=[Depends(require_current_user)])
app.include_router(web3_hot_router, dependencies=[Depends(require_current_user)])
