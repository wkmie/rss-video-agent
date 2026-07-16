from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Web3HotItem
from app.llm.web3_hot_prompts import WEB3_HOT_CONTENT_PROMPT, X_POSTS_SCRIPT_PROMPT
from app.services.web3_hot_service import generate_hot_content, generate_script_from_x_posts


class Web3HotPromptTests(unittest.TestCase):
    def test_prompt_formats_json_example_without_treating_it_as_a_placeholder(self) -> None:
        prompt = WEB3_HOT_CONTENT_PROMPT.format(
            title="Bitcoin test",
            summary="Summary",
            content="Content",
            source_name="X Crypto Search",
            source_type="x_recent_search",
            link="https://example.com/post",
            heat_score=54.0,
            heat_level="gray",
            trend_status="new",
            matched_keywords=json.dumps(["BTC"]),
            raw_metrics=json.dumps({"likes": 10}),
            target_platform="抖音",
            duration="3分钟",
            user_instruction="",
        )

        self.assertIn('"video_titles": ["标题1", "标题2", "标题3"]', prompt)
        self.assertIn("标题：Bitcoin test", prompt)
        self.assertIn("目标平台：抖音", prompt)

    def test_generation_formats_prompt_and_saves_llm_result(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        item = Web3HotItem(
            source_name="X Crypto Search",
            source_type="x_recent_search",
            source_priority="P1",
            title="Bitcoin test",
            content="Content",
            summary="Summary",
            link="https://example.com/post",
            raw_metrics_json='{"likes": 10}',
            matched_keywords_json='["BTC"]',
            entities_json="[]",
            content_hash="a" * 64,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        expected = {
            "video_titles": ["标题1", "标题2", "标题3"],
            "cover_titles": ["封面1", "封面2", "封面3"],
            "video_tags": ["#BTC", "#Web3"],
            "script": "测试口播文案",
        }

        class FakeLLMClient:
            enabled = True

            async def chat(self, prompt: str, temperature: float = 0.7) -> str:
                self_prompt = prompt
                if "Bitcoin test" not in self_prompt:
                    raise AssertionError("热点标题未写入提示词")
                return json.dumps(expected, ensure_ascii=False)

        try:
            with patch("app.services.web3_hot_service.LLMClient", return_value=FakeLLMClient()):
                result = asyncio.run(generate_hot_content(db, item.id, use_llm=True))
            self.assertEqual(result["video_titles"], expected["video_titles"])
            self.assertEqual(result["video_tags"], expected["video_tags"])
            self.assertEqual(result["script"], expected["script"])
            self.assertIsInstance(result["id"], int)
        finally:
            db.close()

    def test_multiple_x_posts_generate_one_script(self) -> None:
        captured_prompt = ""

        class FakeLLMClient:
            enabled = True

            async def chat(self, prompt: str, temperature: float = 0.7) -> str:
                nonlocal captured_prompt
                captured_prompt = prompt
                return "这是一份综合两条 X 消息生成的口播文案。"

        with patch("app.services.web3_hot_service.LLMClient", return_value=FakeLLMClient()):
            result = asyncio.run(
                generate_script_from_x_posts(
                    ["BTC 市场出现新消息", "另一个账号对该消息提出质疑"],
                    target_platform="视频号",
                    duration="1分钟",
                    user_instruction="保持中立",
                )
            )

        self.assertEqual(result["post_count"], 2)
        self.assertEqual(result["script"], "这是一份综合两条 X 消息生成的口播文案。")
        self.assertIn("[X 消息 1]", captured_prompt)
        self.assertIn("[X 消息 2]", captured_prompt)
        self.assertIn("目标平台：视频号", captured_prompt)
        self.assertIn("只输出完整口播文案", X_POSTS_SCRIPT_PROMPT)

    def test_multiple_x_posts_require_content(self) -> None:
        with self.assertRaisesRegex(ValueError, "至少输入一条"):
            asyncio.run(generate_script_from_x_posts(["", "  "]))


if __name__ == "__main__":
    unittest.main()
