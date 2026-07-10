from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EventCalendar, PreTopic
from app.llm.client import LLMClient, parse_json_object
from app.llm.pre_topic_prompts import PRE_EVENT_TOPIC_PROMPT
from app.services.pre_event_service import event_to_dict


def topic_to_dict(topic: PreTopic) -> dict:
    return {
        "id": topic.id,
        "event_id": topic.event_id,
        "event": event_to_dict(topic.event) if topic.event else None,
        "video_title": topic.video_title,
        "cover_title": topic.cover_title,
        "video_tags": json.loads(topic.video_tags_json or "[]"),
        "topic_reason": topic.topic_reason,
        "script_direction": topic.script_direction,
        "script": topic.script,
        "suggested_publish_time": topic.suggested_publish_time,
        "target_platform": topic.target_platform,
        "duration": topic.duration,
        "status": topic.status,
        "created_at": topic.created_at.isoformat() if topic.created_at else None,
        "updated_at": topic.updated_at.isoformat() if topic.updated_at else None,
    }


def fallback_pre_topic(event: EventCalendar, target_platform: str, duration: str, user_instruction: str = "") -> dict:
    event_time = event.event_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subject = event.asset_or_topic or event.country or event.category
    script = (
        f"先提醒一句，{event.event_name}不是已经发生的结果，而是一个即将到来的关键节点。"
        f"从公开信息看，事件时间在 {event_time}，来源是{event.source}。"
        f"这类事件值得提前关注，是因为它可能影响{subject}相关的市场情绪、行业判断和后续叙事。"
        "普通用户不需要提前下结论，更应该看三个信号：第一，事件前市场是否已经提前定价；第二，事件当天官方信息和预期是否有差异；第三，事件之后资金、用户和舆论会不会改变方向。"
        "目前公开信息有限，具体细节仍需以原始来源为准。你觉得这件事会成为真正的转折点，还是只是一轮短期热度？可以在评论区留下你的判断。"
    )
    return {
        "video_title": "这个节点要提前看",
        "cover_title": "提前关注",
        "video_tags": ["#事前选题", f"#{event.category}", "#热点解读", "#KOL口播", "#趋势观察", "#风险提醒", "#事件日历", "#短视频文案"],
        "topic_reason": f"{event.event_name} 是未来事件，适合提前教育用户关注预期差和关键变量。",
        "script_direction": f"围绕事件背景、预期差、影响路径和普通用户应关注的信号展开，平台适配 {target_platform}。",
        "script": script,
        "suggested_publish_time": (event.event_time - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M"),
    }


async def generate_pre_topic(
    db: Session,
    event_id: int,
    target_platform: str = "视频号",
    duration: str = "3分钟",
    user_instruction: str = "",
    use_llm: bool = True,
) -> dict:
    event = db.get(EventCalendar, event_id)
    if not event:
        raise ValueError("Event not found")

    result = fallback_pre_topic(event, target_platform, duration, user_instruction)
    client = LLMClient()
    if use_llm and client.enabled:
        prompt = PRE_EVENT_TOPIC_PROMPT.format(
            event_name=event.event_name,
            event_type=event.event_type,
            category=event.category,
            event_time=event.event_time.isoformat(),
            country_or_asset=event.asset_or_topic or event.country or "",
            source=event.source,
            source_url=event.source_url or "",
            description=event.description or "",
            keywords=event.keywords or "[]",
            importance_level=event.importance_level,
            impact_score=event.impact_score or "",
            expected_value=event.expected_value or "",
            previous_value=event.previous_value or "",
            target_platform=target_platform,
            duration=duration,
            user_instruction=user_instruction or "无",
        )
        parsed = parse_json_object(await client.chat(prompt, temperature=0.75))
        if parsed:
            result.update(parsed)

    topic = PreTopic(
        event_id=event.id,
        video_title=result.get("video_title", ""),
        cover_title=result.get("cover_title", ""),
        video_tags_json=json.dumps(result.get("video_tags", []), ensure_ascii=False),
        topic_reason=result.get("topic_reason", ""),
        script_direction=result.get("script_direction", ""),
        script=result.get("script", ""),
        suggested_publish_time=result.get("suggested_publish_time", ""),
        target_platform=target_platform,
        duration=duration,
        status="topic_generated",
    )
    event.status = "topic_generated"
    event.updated_at = datetime.now(timezone.utc)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic_to_dict(topic)


def list_pre_topics(db: Session, status: Optional[str] = None, limit: int = 100) -> list[dict]:
    stmt = select(PreTopic)
    if status and status != "全部":
        stmt = stmt.where(PreTopic.status == status)
    stmt = stmt.order_by(PreTopic.created_at.desc()).limit(limit)
    return [topic_to_dict(topic) for topic in db.scalars(stmt).all()]


def update_pre_topic_status(db: Session, topic_id: int, status: str) -> dict:
    topic = db.get(PreTopic, topic_id)
    if not topic:
        raise ValueError("Pre topic not found")
    topic.status = status
    topic.updated_at = datetime.now(timezone.utc)
    if topic.event:
        topic.event.status = status
        topic.event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(topic)
    return topic_to_dict(topic)
