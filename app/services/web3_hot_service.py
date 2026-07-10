from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.db.models import Web3HotGeneratedContent, Web3HotItem, Web3HotScore
from app.llm.client import LLMClient, parse_json_object
from app.llm.web3_hot_prompts import WEB3_HOT_CONTENT_PROMPT
from app.services.web3_hot_collectors import HOT_COLLECTORS
from app.services.web3_hot_collectors.base import HotFeedItem
from app.services.web3_hot_scoring import compute_scores


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_sources() -> list[dict[str, Any]]:
    data = load_json(BASE_DIR / "config" / "web3_hot_sources.json")
    return data.get("sources", [])


def load_keywords() -> dict[str, Any]:
    return load_json(BASE_DIR / "config" / "web3_hot_keywords.json")


def content_hash(item: HotFeedItem) -> str:
    raw = f"{item.title.strip()}|{item.link or ''}|{item.source_name}"
    return sha256(raw.encode("utf-8")).hexdigest()


def normalize_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def match_keywords(text: str, keywords_config: dict[str, Any]) -> tuple[list[str], list[str], bool]:
    lowered = text.lower()
    matched: list[str] = []
    entities: list[str] = []
    for group in ("core_assets", "entities", "hot_actions", "risk_keywords"):
        for keyword in keywords_config.get(group, []):
            if keyword.lower() in lowered and keyword not in matched:
                matched.append(keyword)
            if group in {"core_assets", "entities"} and keyword.lower() in lowered and keyword not in entities:
                entities.append(keyword)
    excluded = any(keyword.lower() in lowered for keyword in keywords_config.get("exclude_keywords", []))
    return matched, entities, excluded


def latest_score_subquery():
    return (
        select(Web3HotScore.item_id, func.max(Web3HotScore.id).label("score_id"))
        .group_by(Web3HotScore.item_id)
        .subquery()
    )


def score_to_dict(score: Web3HotScore | None) -> dict[str, Any]:
    if not score:
        return {
            "heat_score": 0,
            "heat_level": "gray",
            "trend_status": "new",
            "score_detail": {},
        }
    try:
        detail = json.loads(score.score_detail_json or "{}")
    except json.JSONDecodeError:
        detail = {}
    return {
        "heat_score": score.heat_score,
        "recency_score": score.recency_score,
        "engagement_score": score.engagement_score,
        "source_weight_score": score.source_weight_score,
        "keyword_score": score.keyword_score,
        "velocity_score": score.velocity_score,
        "risk_score": score.risk_score,
        "confidence_score": score.confidence_score,
        "heat_level": score.heat_level,
        "trend_status": score.trend_status,
        "score_detail": detail,
    }


def item_to_dict(item: Web3HotItem, score: Web3HotScore | None = None) -> dict[str, Any]:
    try:
        raw_metrics = json.loads(item.raw_metrics_json or "{}")
    except json.JSONDecodeError:
        raw_metrics = {}
    try:
        matched_keywords = json.loads(item.matched_keywords_json or "[]")
    except json.JSONDecodeError:
        matched_keywords = []
    try:
        entities = json.loads(item.entities_json or "[]")
    except json.JSONDecodeError:
        entities = []
    data = {
        "id": item.id,
        "source_name": item.source_name,
        "source_type": item.source_type,
        "source_priority": item.source_priority,
        "title": item.title,
        "content": item.content,
        "summary": item.summary,
        "link": item.link,
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "language": item.language,
        "raw_metrics": raw_metrics,
        "matched_keywords": matched_keywords,
        "entities": entities,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
    data.update(score_to_dict(score))
    return data


def get_latest_score(db: Session, item_id: int) -> Web3HotScore | None:
    return db.execute(
        select(Web3HotScore).where(Web3HotScore.item_id == item_id).order_by(desc(Web3HotScore.id)).limit(1)
    ).scalar_one_or_none()


def upsert_score(db: Session, item: Web3HotItem, keywords_config: dict[str, Any]) -> Web3HotScore:
    previous = get_latest_score(db, item.id)
    data = compute_scores(db, item, keywords_config, previous.heat_score if previous else None)
    score = Web3HotScore(item_id=item.id, **data)
    db.add(score)
    return score


async def fetch_and_store_hot_items(
    db: Session,
    source_type: str | None = None,
    keyword: str | None = None,
) -> dict[str, Any]:
    sources = load_sources()
    keywords_config = load_keywords()
    fetched_count = inserted_count = updated_count = skipped_count = 0
    errors: list[str] = []
    max_items = settings.web3_hot_max_items_per_source

    for collector_cls in HOT_COLLECTORS:
        collector = collector_cls(sources, max_items)
        result = await collector.fetch(source_type=source_type, keyword=keyword)
        errors.extend(result.errors)
        for feed_item in result.items:
            fetched_count += 1
            text = f"{feed_item.title} {strip_html(feed_item.summary)} {strip_html(feed_item.content)}"
            matched_keywords, entities, excluded = match_keywords(text, keywords_config)
            if excluded:
                skipped_count += 1
                continue
            hash_value = content_hash(feed_item)
            existing = db.execute(select(Web3HotItem).where(Web3HotItem.content_hash == hash_value)).scalar_one_or_none()
            now = utcnow()
            if existing:
                existing.summary = strip_html(feed_item.summary) or existing.summary
                existing.content = strip_html(feed_item.content) or existing.content
                existing.raw_metrics_json = json.dumps(feed_item.raw_metrics, ensure_ascii=False)
                existing.matched_keywords_json = json.dumps(matched_keywords, ensure_ascii=False)
                existing.entities_json = json.dumps(entities, ensure_ascii=False)
                existing.fetched_at = now
                existing.updated_at = now
                item = existing
                updated_count += 1
            else:
                item = Web3HotItem(
                    source_name=feed_item.source_name,
                    source_type=feed_item.source_type,
                    source_priority=feed_item.source_priority,
                    title=feed_item.title.strip(),
                    content=strip_html(feed_item.content),
                    summary=strip_html(feed_item.summary),
                    link=feed_item.link,
                    author=feed_item.author,
                    published_at=normalize_dt(feed_item.published_at),
                    fetched_at=now,
                    language=feed_item.language,
                    raw_metrics_json=json.dumps(feed_item.raw_metrics, ensure_ascii=False),
                    matched_keywords_json=json.dumps(matched_keywords, ensure_ascii=False),
                    entities_json=json.dumps(entities, ensure_ascii=False),
                    content_hash=hash_value,
                )
                db.add(item)
                db.flush()
                inserted_count += 1
            upsert_score(db, item, keywords_config)
    db.commit()
    return {
        "fetched_count": fetched_count,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


def list_hot_items(
    db: Session,
    limit: int = 30,
    heat_level: str | None = None,
    trend_status: str | None = None,
    keyword: str | None = None,
    source_type: str | None = None,
    hours: int = 24,
) -> list[dict[str, Any]]:
    score_ids = latest_score_subquery()
    query = (
        select(Web3HotItem, Web3HotScore)
        .join(score_ids, score_ids.c.item_id == Web3HotItem.id)
        .join(Web3HotScore, Web3HotScore.id == score_ids.c.score_id)
        .where(Web3HotItem.fetched_at >= utcnow() - timedelta(hours=hours))
    )
    if heat_level:
        query = query.where(Web3HotScore.heat_level == heat_level)
    if trend_status:
        query = query.where(Web3HotScore.trend_status == trend_status)
    if source_type:
        query = query.where(Web3HotItem.source_type == source_type)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(
            (Web3HotItem.title.like(like))
            | (Web3HotItem.summary.like(like))
            | (Web3HotItem.matched_keywords_json.like(like))
        )
    rows = db.execute(query.order_by(desc(Web3HotScore.heat_score)).limit(limit)).all()
    return [item_to_dict(item, score) for item, score in rows]


def get_hot_item_detail(db: Session, item_id: int) -> dict[str, Any]:
    item = db.get(Web3HotItem, item_id)
    if not item:
        raise ValueError("Hot item not found")
    score = get_latest_score(db, item.id)
    detail = item_to_dict(item, score)
    tokens = set(re.findall(r"[A-Za-z0-9]{3,}|[\u4e00-\u9fff]{2,}", item.title.lower()))
    related = []
    if tokens:
        for other in db.execute(select(Web3HotItem).where(Web3HotItem.id != item.id).order_by(desc(Web3HotItem.fetched_at)).limit(200)).scalars():
            other_tokens = set(re.findall(r"[A-Za-z0-9]{3,}|[\u4e00-\u9fff]{2,}", other.title.lower()))
            if len(tokens & other_tokens) / max(len(tokens), 1) >= 0.45:
                related.append({"source_name": other.source_name, "title": other.title, "link": other.link})
            if len(related) >= 10:
                break
    detail["related_sources"] = related
    detail["is_rumor_like"] = item.source_type == "x_recent_search" and len(related) == 0
    detail["suitable_for_video_now"] = (score.heat_score if score else 0) >= 60 and not detail["is_rumor_like"]
    return detail


def ticker_items(db: Session, limit: int = 15) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "summary": item["summary"],
            "source_name": item["source_name"],
            "heat_score": item["heat_score"],
            "heat_level": item["heat_level"],
            "trend_status": item["trend_status"],
            "published_at": item["published_at"],
            "link": item["link"],
        }
        for item in list_hot_items(db, limit=limit, hours=settings.web3_hot_item_ttl_hours)
    ]


def hot_stats(db: Session) -> dict[str, Any]:
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    score_ids = latest_score_subquery()
    rows = db.execute(
        select(Web3HotScore.heat_level, func.count())
        .join(score_ids, score_ids.c.score_id == Web3HotScore.id)
        .group_by(Web3HotScore.heat_level)
    ).all()
    levels = {level: count for level, count in rows}
    latest_fetch = db.execute(select(func.max(Web3HotItem.fetched_at))).scalar_one_or_none()
    sources = load_sources()
    return {
        "today_count": db.execute(select(func.count()).select_from(Web3HotItem).where(Web3HotItem.fetched_at >= today_start)).scalar_one(),
        "red_count": levels.get("red", 0),
        "yellow_count": levels.get("yellow", 0),
        "gray_count": levels.get("gray", 0),
        "latest_refresh_time": latest_fetch.isoformat() if latest_fetch else None,
        "enabled_source_count": len([source for source in sources if source.get("enabled", True)]),
        "error_count": 0,
        "x_configured": bool(settings.x_bearer_token),
        "lunarcrush_configured": bool(settings.lunarcrush_api_key),
    }


def fallback_generated_content(item: Web3HotItem, score: Web3HotScore | None, duration: str) -> dict[str, Any]:
    heat = score.heat_score if score else 0
    script = (
        f"先说结论，{item.title} 这条 Web3 热点现在值得关注。\n\n"
        f"它来自 {item.source_name}，当前系统热度分是 {heat:.1f}。"
        f"{item.summary or '公开摘要信息还不多，发布前需要打开原文核对关键事实。'}\n\n"
        "这类消息不能只看标题。真正重要的是它会不会影响市场情绪、交易所动作、项目方信誉，或者用户对风险的判断。"
        "如果它涉及黑客攻击、ETF、稳定币、交易所或者 Strategy 这类核心关键词，后续发酵速度通常会更快。\n\n"
        "但也要注意，单一来源的信息不能直接当成最终事实。我们会继续看有没有官方确认，或者是否出现更多媒体跟进。"
        "你觉得这条消息会继续发酵吗？评论区说说你的判断。"
    )
    return {
        "video_titles": ["这条热点不简单", "Web3又有新信号", "市场正在盯着它"],
        "cover_titles": ["热点升温", "风险信号", "盯紧它"],
        "video_tags": ["#Web3", "#加密货币", "#比特币", "#Crypto", "#热点解读", "#区块链", "#市场情绪", "#风险提醒"],
        "script": script,
    }


async def generate_hot_content(
    db: Session,
    item_id: int,
    target_platform: str = "抖音",
    duration: str = "3分钟",
    user_instruction: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    item = db.get(Web3HotItem, item_id)
    if not item:
        raise ValueError("Hot item not found")
    score = get_latest_score(db, item.id)
    if use_llm:
        client = LLMClient()
        if client.enabled:
            prompt = WEB3_HOT_CONTENT_PROMPT.format(
                title=item.title,
                summary=item.summary or "",
                content=item.content or "",
                source_name=item.source_name,
                source_type=item.source_type,
                link=item.link or "",
                heat_score=score.heat_score if score else 0,
                heat_level=score.heat_level if score else "gray",
                trend_status=score.trend_status if score else "new",
                matched_keywords=item.matched_keywords_json,
                raw_metrics=item.raw_metrics_json,
                user_instruction=user_instruction,
                target_platform=target_platform,
                duration=duration,
            )
            output = await client.chat(prompt, temperature=0.72)
            parsed = parse_json_object(output)
            if parsed:
                data = parsed
            else:
                data = fallback_generated_content(item, score, duration)
        else:
            data = fallback_generated_content(item, score, duration)
    else:
        data = fallback_generated_content(item, score, duration)

    record = Web3HotGeneratedContent(
        item_id=item.id,
        video_titles_json=json.dumps(data.get("video_titles", []), ensure_ascii=False),
        cover_titles_json=json.dumps(data.get("cover_titles", []), ensure_ascii=False),
        video_tags_json=json.dumps(data.get("video_tags", []), ensure_ascii=False),
        script=data.get("script", ""),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "item_id": item.id, **data}
