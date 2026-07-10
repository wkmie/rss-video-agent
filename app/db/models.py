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


class EventCalendar(Base):
    __tablename__ = "event_calendar"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_event_calendar_content_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_name: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    asset_or_topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(200), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance_level: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    expected_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    previous_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actual_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    pre_topics: Mapped[list["PreTopic"]] = relationship(back_populates="event")


class PreTopic(Base):
    __tablename__ = "pre_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("event_calendar.id"), index=True)
    video_title: Mapped[str] = mapped_column(Text)
    cover_title: Mapped[str] = mapped_column(Text)
    video_tags_json: Mapped[str] = mapped_column(Text)
    topic_reason: Mapped[str] = mapped_column(Text)
    script_direction: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    suggested_publish_time: Mapped[str] = mapped_column(String(100))
    target_platform: Mapped[str] = mapped_column(String(50), default="视频号")
    duration: Mapped[str] = mapped_column(String(50), default="3分钟")
    status: Mapped[str] = mapped_column(String(30), default="topic_generated", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event: Mapped[EventCalendar] = relationship(back_populates="pre_topics")


class Web3HotItem(Base):
    __tablename__ = "web3_hot_items"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_web3_hot_items_content_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(200), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_priority: Mapped[str] = mapped_column(String(10), default="P2", index=True)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    language: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    matched_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    scores: Mapped[list["Web3HotScore"]] = relationship(back_populates="item")
    generated_contents: Mapped[list["Web3HotGeneratedContent"]] = relationship(back_populates="item")


class Web3HotScore(Base):
    __tablename__ = "web3_hot_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("web3_hot_items.id"), index=True)
    heat_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    recency_score: Mapped[float] = mapped_column(Float, default=0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0)
    source_weight_score: Mapped[float] = mapped_column(Float, default=0)
    keyword_score: Mapped[float] = mapped_column(Float, default=0)
    velocity_score: Mapped[float] = mapped_column(Float, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    heat_level: Mapped[str] = mapped_column(String(20), default="gray", index=True)
    trend_status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    score_detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    item: Mapped[Web3HotItem] = relationship(back_populates="scores")


class Web3HotGeneratedContent(Base):
    __tablename__ = "web3_hot_generated_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("web3_hot_items.id"), index=True)
    video_titles_json: Mapped[str] = mapped_column(Text)
    cover_titles_json: Mapped[str] = mapped_column(Text)
    video_tags_json: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[Web3HotItem] = relationship(back_populates="generated_contents")
