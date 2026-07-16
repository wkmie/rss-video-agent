from __future__ import annotations

import json
import unittest

from app.trading_cognition.prompts import build_prompt
from app.trading_cognition.retriever import normalize_query, retrieve_knowledge
from app.trading_cognition.service import fallback_content_package


class TradingCognitionTests(unittest.TestCase):
    def test_stop_loss_question_retrieves_stop_loss_first(self) -> None:
        cards = retrieve_knowledge("交易为什么要设置止损？")
        self.assertEqual(cards[0].id, "stop_loss")

    def test_common_typo_is_normalized(self) -> None:
        self.assertEqual(normalize_query("交易为社么要设置止损？"), "交易为什么要设置止损")
        cards = retrieve_knowledge("交易为社么要设置止损？")
        self.assertEqual(cards[0].id, "stop_loss")

    def test_prompt_contains_retrieved_evidence_and_safety_boundary(self) -> None:
        cards = retrieve_knowledge("为什么要止损？")
        prompt = build_prompt("为什么要止损？", "抖音", "1分钟", cards)
        self.assertIn("止损不是看空", prompt)
        self.assertIn("不构成投资建议", prompt)
        self.assertIn("不要冒充原创作者本人", prompt)

    def test_fallback_is_a_valid_content_package(self) -> None:
        cards = retrieve_knowledge("交易为什么要设置止损？")
        package = json.loads(fallback_content_package("交易为什么要设置止损？", "抖音", "1分钟", cards))
        self.assertEqual(set(package), {"video_titles", "cover_titles", "video_tags", "script"})
        self.assertIn("止损", package["script"])
        self.assertIn("不构成任何投资建议", package["script"])


if __name__ == "__main__":
    unittest.main()
