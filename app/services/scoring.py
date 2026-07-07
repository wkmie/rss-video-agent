from __future__ import annotations

import json
import re

from app.db.models import Article


HOT_WORDS = {
    "crypto": ["bitcoin", "btc", "ethereum", "etf", "sec", "binance", "stablecoin", "hack", "airdrop"],
    "ai": ["openai", "google", "anthropic", "model", "agent", "robot", "gpu", "nvidia", "research"],
    "tech": ["launch", "lawsuit", "security", "privacy", "startup", "funding", "china", "apple", "meta"],
}
CONFLICT_WORDS = ["ban", "crackdown", "lawsuit", "controversy", "risk", "warn", "fight", "vs", "drop", "surge", "scam", "hack"]
CHINESE_HOT_WORDS = ["比特币", "人工智能", "大模型", "英伟达", "监管", "黑客", "融资", "争议", "预测"]


def score_article(article: Article) -> tuple[int, dict[str, int]]:
    text = f"{article.title} {article.summary or ''}".lower()
    zh_text = f"{article.title} {article.summary or ''}"
    hot_hits = sum(1 for words in HOT_WORDS.values() for word in words if word in text)
    hot_hits += sum(1 for word in CHINESE_HOT_WORDS if word in zh_text)
    conflict_hits = sum(1 for word in CONFLICT_WORDS if word in text)

    heat = min(20, 8 + hot_hits * 3)
    conflict = min(20, 6 + conflict_hits * 4)
    understandability = 18 if len(article.title) <= 90 else 14
    account_match = 18 if article.category in {"crypto_news", "ai_news", "tech_news"} else 12
    conversion = min(20, 8 + hot_hits * 2 + conflict_hits * 2)

    detail = {
        "热度": heat,
        "冲突感": conflict,
        "普通用户理解度": understandability,
        "账号匹配度": account_match,
        "短视频转化潜力": conversion,
    }
    return sum(detail.values()), detail


def recommendation_level(score: float) -> str:
    if score >= 78:
        return "高"
    if score >= 58:
        return "中"
    return "低"


def suggested_format(score: float) -> str:
    if score >= 85:
        return "3分钟解析"
    if score >= 72:
        return "1分钟观点"
    if score >= 58:
        return "30秒快讯"
    return "5分钟深度"


def score_detail_json(article: Article) -> str:
    _, detail = score_article(article)
    return json.dumps(detail, ensure_ascii=False)


def title_to_zh(title: str, language: str) -> str:
    if language == "zh":
        return title
    text = re.sub(r"\s*[-|]\s*[^-|]+$", "", title).strip()
    return f"中文解读：{text}"
