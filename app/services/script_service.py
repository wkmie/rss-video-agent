import re

from sqlalchemy.orm import Session

from app.db.models import Article, ScriptGeneration
from app.llm.client import LLMClient
from app.llm.prompts import CUSTOM_ONLY_SCRIPT_PROMPT, VIDEO_SCRIPT_PROMPT
from app.services.scoring import title_to_zh


WORD_TARGETS = {
    "30秒": "150-220 字",
    "1分钟": "300-450 字",
    "3分钟": "800-1000 字",
    "5分钟": "1300-1600 字",
    "10分钟": "2500-3000 字",
}


def fallback_script(
    topic: str,
    platform: str,
    duration: str,
    title: str = "",
    summary: str = "",
    source_name: str = "",
    link: str = "",
    custom_prompt: str = "",
) -> str:
    subject = topic or title or "这个热点"
    source_line = f"这条信息来自{source_name}。" if source_name else ""
    detail_line = summary or "目前公开摘要给出的细节还不多，发布前最好打开原文再核对一次关键事实。"
    platform_line = {
        "抖音": "在抖音上，这类内容开头一定要先给判断，不要慢慢铺垫。",
        "视频号": "在视频号里，这类内容要把背景讲清楚，让不常刷热点的人也能听懂。",
        "小红书": "在小红书上，这类内容要更像是在帮用户避坑和做判断。",
        "B站": "在 B 站上，这类内容可以多讲一点逻辑，但别把它讲成报告。",
    }.get(platform, f"在{platform}上，这段内容要尽量贴合平台用户的阅读节奏。")
    return f"""先说结论，{subject}这件事，不能只当成一条普通新闻看。真正值得关注的，是它接下来可能影响谁，以及会不会引发新的连锁反应。

简单讲，现在能确认的信息是：{detail_line}{source_line}

{platform_line}所以这条视频不要堆术语，也不要照着新闻稿念。我们要把问题拆成三层：第一，到底发生了什么；第二，为什么现在发生；第三，普通用户应该关注什么变化。

我的判断是，先不要急着下最终结论。因为 RSS 摘要里的信息通常比较有限，尤其是具体数字、当事方表态和后续时间线，都需要二次核实。但它已经释放出一个信号：相关领域正在出现新的变量，接下来要看市场、用户或者机构会不会给出明确反馈。

如果你只想抓重点，就记住一句话：这件事短期看是新闻，长期看是趋势信号。后面我会继续跟进它的进展，你也可以在评论区说说，你觉得它会继续发酵，还是很快被市场忘掉。"""


def clean_script_output(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
    markers = ["完整口播文案", "口播文案", "正文"]
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1].lstrip("：:\n ")
            break
    cleaned = re.split(r"\n\s*[一二三四五六七八九十]+[、.．]\s*(剪辑|自检|标题|推荐|说明|备注)", cleaned, maxsplit=1)[0].rstrip()
    for end_marker in ["剪辑配图关键词", "剪辑建议", "自检", "标题：", "推荐标题"]:
        if end_marker in cleaned:
            cleaned = cleaned.split(end_marker, 1)[0].rstrip()
    return cleaned


async def generate_from_article(
    db: Session,
    article_id: int,
    duration: str,
    platform: str,
    use_llm: bool = True,
    custom_prompt: str = "",
) -> dict:
    article = db.get(Article, article_id)
    if not article:
        raise ValueError("Article not found")
    topic = title_to_zh(article.title, article.language)
    text = await generate_text(
        topic=topic,
        platform=platform,
        duration=duration,
        title=article.title,
        summary=article.summary or "",
        source_name=article.source_name,
        link=article.link,
        use_llm=use_llm,
        custom_prompt=custom_prompt,
    )
    record = ScriptGeneration(article_id=article.id, topic=None, duration=duration, platform=platform, script_text=text)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "article_id": article.id, "script_text": text}


async def generate_from_topic(
    db: Session,
    topic: str,
    duration: str,
    platform: str,
    use_llm: bool = True,
    custom_prompt: str = "",
) -> dict:
    text = await generate_text(topic=topic, platform=platform, duration=duration, use_llm=use_llm, custom_prompt=custom_prompt)
    record = ScriptGeneration(article_id=None, topic=topic, duration=duration, platform=platform, script_text=text)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "topic": topic, "script_text": text}


async def generate_text(
    topic: str,
    platform: str,
    duration: str,
    title: str = "",
    summary: str = "",
    source_name: str = "",
    link: str = "",
    use_llm: bool = True,
    custom_prompt: str = "",
) -> str:
    client = LLMClient()
    if use_llm:
        if not client.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if custom_prompt.strip():
            prompt = CUSTOM_ONLY_SCRIPT_PROMPT.format(
                custom_prompt=custom_prompt.strip(),
                platform=platform,
                duration=duration,
                topic=topic,
                title=title,
                summary=summary,
                source_name=source_name,
                link=link,
            )
        else:
            prompt = VIDEO_SCRIPT_PROMPT.format(
                platform=platform,
                duration=duration,
                topic=topic,
                title=title,
                summary=summary,
                source_name=source_name,
                link=link,
            )
        try:
            return clean_script_output(await client.chat(prompt, temperature=0.75))
        except Exception as exc:
            raise RuntimeError(f"LLM generation failed: {exc}") from exc
    return fallback_script(topic, platform, duration, title, summary, source_name, link, custom_prompt)
