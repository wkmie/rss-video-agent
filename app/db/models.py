from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_articles_content_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(200), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    title_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    language: Mapped[str] = mapped_column(String(20), default="en")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analyses: Mapped[list["AnalysisResult"]] = relationship(back_populates="article")
    scripts: Mapped[list["ScriptGeneration"]] = relationship(back_populates="article")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    one_sentence_summary: Mapped[str] = mapped_column(Text)
    why_important: Mapped[str] = mapped_column(Text)
    video_angle: Mapped[str] = mapped_column(Text)
    recommended_titles_json: Mapped[str] = mapped_column(Text)
    score_detail_json: Mapped[str] = mapped_column(Text)
    suggested_format: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    article: Mapped[Article] = relationship(back_populates="analyses")


class ScriptGeneration(Base):
    __tablename__ = "script_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[Optional[int]] = mapped_column(ForeignKey("articles.id"), nullable=True, index=True)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[str] = mapped_column(String(50), default="3分钟")
    platform: Mapped[str] = mapped_column(String(50), default="抖音")
    script_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    article: Mapped[Optional[Article]] = relationship(back_populates="scripts")
