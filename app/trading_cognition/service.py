from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.db.models import ScriptGeneration
from app.llm.client import LLMClient, parse_json_object
from app.trading_cognition.knowledge import SOURCE_NAME, SOURCE_NOTICE, KnowledgeCard
from app.trading_cognition.prompts import build_prompt
from app.trading_cognition.retriever import retrieve_knowledge


REQUIRED_PACKAGE_KEYS = ("video_titles", "cover_titles", "video_tags", "script")


def clean_json_output(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    return cleaned


def normalize_content_package(text: str) -> str:
    parsed = parse_json_object(clean_json_output(text))
    if not parsed or not all(key in parsed for key in REQUIRED_PACKAGE_KEYS):
        raise RuntimeError("交易认知模型输出不是有效的内容包 JSON")

    for key in ("video_titles", "cover_titles", "video_tags"):
        if not isinstance(parsed[key], list):
            raise RuntimeError(f"交易认知模型输出字段 {key} 必须是数组")
        parsed[key] = [str(item).strip() for item in parsed[key] if str(item).strip()]
    if not isinstance(parsed["script"], str) or not parsed["script"].strip():
        raise RuntimeError("交易认知模型输出缺少有效口播文案")
    parsed["script"] = parsed["script"].strip()
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def fallback_content_package(
    question: str,
    platform: str,
    duration: str,
    cards: list[KnowledgeCard],
) -> str:
    primary = cards[0]
    supporting = cards[1] if len(cards) > 1 else primary
    script = f"""老师，{question}

你先告诉我：你设置规则，是为了每次都猜对，还是为了猜错的时候还能留在场内？

很多人把它理解反了。他们以为只有不看好后市才需要退出，一旦还期待反弹，就想再等等。但市场会不会反弹，你控制不了。你真正能控制的，是这次判断失效以后，最多付出多大代价。

{primary.belief}

为什么？第一，{primary.reasoning[0]}。第二，{primary.reasoning[1]}。第三，{supporting.reasoning[0]}。

所以别把规则当成对行情的预测。它是你给错误划下的边界。真正能执行的动作只有一个：{primary.action_rule}

记住，交易里最重要的不是每次都对，而是错的时候代价可控，对的时候仍有机会继续。以上是交易认知讨论，不构成任何投资建议。"""
    return json.dumps(
        {
            "video_titles": [
                primary.title,
                f"{question.rstrip('？?')}，你可能理解反了",
                "交易里真正可控的是什么？",
            ],
            "cover_titles": ["给错误划边界", "先活下来", "别等市场原谅"],
            "video_tags": ["#交易", "#交易认知", "#交易心得", "#风险管理", "#交易系统", "#交易心理"],
            "script": script,
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_trading_cognition(
    db: Session,
    question: str,
    duration: str,
    platform: str,
    use_llm: bool = True,
    knowledge_limit: int = 4,
) -> dict:
    normalized_question = question.strip()
    cards = retrieve_knowledge(normalized_question, limit=knowledge_limit)

    if use_llm:
        client = LLMClient()
        if not client.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        prompt = build_prompt(normalized_question, platform, duration, cards)
        try:
            output = await client.chat(prompt, temperature=0.72)
            script_text = normalize_content_package(output)
        except Exception as exc:
            raise RuntimeError(f"交易认知文案生成失败：{exc}") from exc
    else:
        script_text = fallback_content_package(normalized_question, platform, duration, cards)

    record = ScriptGeneration(
        article_id=None,
        topic=f"[交易认知] {normalized_question}",
        duration=duration,
        platform=platform,
        script_text=script_text,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "question": normalized_question,
        "source_module": "trading_cognition",
        "source_name": SOURCE_NAME,
        "source_notice": SOURCE_NOTICE,
        "matched_knowledge": [card.to_public_dict() for card in cards],
        "script_text": script_text,
    }
