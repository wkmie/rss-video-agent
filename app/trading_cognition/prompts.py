from __future__ import annotations

from app.trading_cognition.knowledge import SOURCE_NAME, SOURCE_NOTICE, KnowledgeCard


WORD_TARGETS = {
    "30秒": "150-220字",
    "1分钟": "300-450字",
    "3分钟": "800-1000字",
    "5分钟": "1300-1600字",
    "10分钟": "2500-3000字",
}


TRADING_COGNITION_PROMPT = """
你是中文短视频团队里的“交易认知文案编辑”。请根据用户问题和给定知识卡片，生成一个可以直接审核、修改和拍摄的内容包。

内容来源：{source_name}
来源说明：{source_notice}
用户问题：{question}
目标平台：{platform}
目标时长：{duration}
建议字数：{word_target}

只允许使用下面知识卡片中的认知结论作为核心依据：
{knowledge_context}

写作框架：
1. 用学员困惑、尖锐反问或反常识判断开场，前10秒必须命中问题；
2. 先揭露常见误解，再完成一次认知反转；
3. 用算账、场景、因果链或分步骤证明，不要空喊口号；
4. 最后收缩成一条可以执行和复盘的规则；
5. 可采用“学员一句困惑—导师追问—证明—规则”的对话感，但不要冒充原创作者本人，也不要声称是其原话；
6. 多用短句，不用Emoji，不写研报腔，不堆术语；
7. 不提供具体品种、点位、买卖信号、仓位比例或收益承诺；不鼓励高频、重仓、追涨杀跌；
8. 必须自然说明内容是交易认知讨论，不构成投资建议；
9. 若知识卡片不能覆盖问题，直接说明“当前交易认知资料未覆盖”，不要编造答案。

请严格输出合法JSON，不要输出JSON以外的任何内容：
{{
  "video_titles": ["标题1", "标题2", "标题3"],
  "cover_titles": ["封面1", "封面2", "封面3"],
  "video_tags": ["#交易", "#交易认知", "#交易心得"],
  "script": "完整口播文案"
}}
"""


def build_prompt(question: str, platform: str, duration: str, cards: list[KnowledgeCard]) -> str:
    context = "\n\n".join(card.to_prompt_context() for card in cards)
    return TRADING_COGNITION_PROMPT.format(
        source_name=SOURCE_NAME,
        source_notice=SOURCE_NOTICE,
        question=question,
        platform=platform,
        duration=duration,
        word_target=WORD_TARGETS.get(duration, "与目标时长匹配"),
        knowledge_context=context,
    )
