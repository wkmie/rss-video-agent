from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnalysisResult, Article
from app.llm.client import LLMClient, parse_json_object
from app.llm.prompts import NEWS_ANALYSIS_PROMPT
from app.rss.fetcher import fetch_all_sources
from app.services.keyword_filter import article_query
from app.services.scoring import recommendation_level, score_article, suggested_format, title_to_zh


def article_to_dict(article: Article) -> dict:
    return {
        "id": article.id,
        "source_name": article.source_name,
        "source_url": article.source_url,
        "title": article.title,
        "title_zh": article.title_zh or title_to_zh(article.title, article.language),
        "link": article.link,
        "summary": article.summary,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "category": article.category,
        "language": article.language,
        "score": article.score,
        "recommendation_level": recommendation_level(article.score),
    }


async def fetch_and_store(db: Session) -> dict:
    rss_articles, errors = await fetch_all_sources()
    created = 0
    updated = 0
    for item in rss_articles:
        existing = db.scalar(select(Article).where(Article.content_hash == item.content_hash))
        if existing:
            updated += 1
            continue
        article = Article(
            source_name=item.source_name,
            source_url=item.source_url,
            title=item.title,
            title_zh=title_to_zh(item.title, item.language),
            link=item.link,
            summary=item.summary,
            published_at=item.published_at,
            category=item.category,
            language=item.language,
            content_hash=item.content_hash,
            score=0,
        )
        score, _ = score_article(article)
        article.score = score
        db.add(article)
        created += 1
    db.commit()
    return {"fetched": len(rss_articles), "created": created, "duplicates": updated, "errors": errors}


def list_articles(
    db: Session,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    time_range: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    return [article_to_dict(article) for article in article_query(db, category, keyword, time_range, limit)]


def fallback_analysis(article: Article) -> dict:
    score, detail = score_article(article)
    title_zh = title_to_zh(article.title, article.language)
    angle = "用普通人视角解释这件事会影响谁、改变什么、哪里有争议。"
    return {
        "title_zh": title_zh,
        "one_sentence_summary": f"{title_zh}。信息来自 RSS 摘要，发布前建议打开原文二次核实。",
        "why_important": "这条消息有明确的新信息点，适合用短视频快速解释背景、影响和潜在争议。",
        "video_angle": angle,
        "recommended_titles": [
            title_zh[:12],
            "这事不简单",
            "普通人该看懂",
        ],
        "score": score,
        "score_detail": detail,
        "suggested_format": suggested_format(score),
    }


async def analyze_article(db: Session, article_id: int, use_llm: bool = True) -> dict:
    article = db.get(Article, article_id)
    if not article:
        raise ValueError("Article not found")

    result = fallback_analysis(article)
    client = LLMClient()
    if use_llm and client.enabled:
        prompt = NEWS_ANALYSIS_PROMPT.format(
            source_name=article.source_name,
            category=article.category,
            language=article.language,
            title=article.title,
            summary=article.summary or "",
            link=article.link,
            published_at=article.published_at.isoformat() if article.published_at else "",
        )
        try:
            parsed = parse_json_object(await client.chat(prompt, temperature=0.4))
            if parsed:
                result.update(parsed)
        except Exception:
            pass

    article.title_zh = result.get("title_zh") or article.title_zh
    article.score = float(result.get("score") or article.score)
    analysis = AnalysisResult(
        article_id=article.id,
        one_sentence_summary=result["one_sentence_summary"],
        why_important=result["why_important"],
        video_angle=result["video_angle"],
        recommended_titles_json=json.dumps(result["recommended_titles"], ensure_ascii=False),
        score_detail_json=json.dumps(result["score_detail"], ensure_ascii=False),
        suggested_format=result["suggested_format"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return {
        "id": analysis.id,
        "article": article_to_dict(article),
        "one_sentence_summary": analysis.one_sentence_summary,
        "why_important": analysis.why_important,
        "video_angle": analysis.video_angle,
        "recommended_titles": json.loads(analysis.recommended_titles_json),
        "score_detail": json.loads(analysis.score_detail_json),
        "suggested_format": analysis.suggested_format,
    }


def top_topic_pool(db: Session, category: Optional[str], keyword: Optional[str], time_range: Optional[str], limit: int = 10) -> list[dict]:
    articles = article_query(db, category, keyword, time_range, limit)
    return [article_to_dict(article) for article in articles[:limit]]
