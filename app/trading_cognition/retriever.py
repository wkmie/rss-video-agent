from __future__ import annotations

import re

from app.trading_cognition.knowledge import KNOWLEDGE_CARDS, KnowledgeCard


TYPO_NORMALIZATIONS = {
    "为社么": "为什么",
    "为什吗": "为什么",
    "止埙": "止损",
    "之损": "止损",
    "仓为": "仓位",
}


def normalize_query(query: str) -> str:
    value = query.strip().lower()
    for typo, normalized in TYPO_NORMALIZATIONS.items():
        value = value.replace(typo, normalized)
    return re.sub(r"[\s，。！？、,.!?:：;；‘’“”\-_/]+", "", value)


def character_ngrams(text: str, size: int = 2) -> set[str]:
    if len(text) < size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def card_score(query: str, card: KnowledgeCard) -> float:
    normalized = normalize_query(query)
    if not normalized:
        return 0.0

    score = 0.0
    for keyword in card.keywords:
        keyword_normalized = normalize_query(keyword)
        if keyword_normalized and keyword_normalized in normalized:
            score += 10.0 + min(len(keyword_normalized), 4)

    searchable = normalize_query(
        "".join((card.title, card.belief, card.action_rule, *card.reasoning, *card.keywords))
    )
    query_grams = character_ngrams(normalized)
    card_grams = character_ngrams(searchable)
    if query_grams:
        overlap = len(query_grams & card_grams)
        score += overlap / len(query_grams) * 8.0
    return score


def retrieve_knowledge(query: str, limit: int = 4) -> list[KnowledgeCard]:
    ranked = sorted(
        ((card_score(query, card), card) for card in KNOWLEDGE_CARDS),
        key=lambda item: (-item[0], item[1].id),
    )
    selected = [card for score, card in ranked if score > 0][: max(1, limit)]
    return selected or list(KNOWLEDGE_CARDS[: max(1, limit)])
