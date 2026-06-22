from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_news import router as news_router
from app.api.routes_script import router as script_router
from app.db.database import init_db


app = FastAPI(title="RSS Video Agent", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(news_router)
app.include_router(script_router)
