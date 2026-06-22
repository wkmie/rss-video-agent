from sqlalchemy.orm import Session

from app.db.models import Article, ScriptGeneration
from app.llm.client import LLMClient
from app.llm.prompts import VIDEO_SCRIPT_PROMPT
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
) -> str:
    subject = topic or title or "这个热点"
    fact_note = f"信息来源：{source_name}，原文链接：{link}" if source_name or link else "请在发布前补充权威来源并二次核实。"
    words = WORD_TARGETS.get(duration, "800-1000 字")
    return f"""一、选题判断
【核心看点】{subject}
【点击动机】这件事看起来像普通新闻，但背后可能影响普通人的判断和选择。
【最大冲突】新变化和旧认知之间的冲突。
【适合平台】{platform}
【是否适合引到预测市场 / Web3】中等，适合在结尾引导用户讨论结果会怎么走。
【建议视频时长】{duration}

二、推荐标题
1. 这事不简单
2. 真相来了
3. 别只看热闹

三、视频骨架
1. 前 10 秒抛出冲突
2. 用一句话讲清发生了什么
3. 解释为什么普通人要关注
4. 给出自己的判断
5. 提醒不确定信息要核实
6. 引导评论和后续追踪

四、完整口播文案
先别急着把这条消息当成普通新闻看。真正值得关注的，不是它发生了，而是它接下来可能带来的连锁反应。

简单说，{subject}。{summary or "目前 RSS 摘要给出的信息有限，发布前建议打开原文确认细节。"}

为什么这事适合做成短视频？因为它有三个点：第一，普通人能听懂；第二，它有明显的判断空间；第三，它不是单纯复述新闻，而是可以讨论“接下来会怎样”。

我的看法是，先不要急着下结论。你可以把它拆成两个问题：这件事影响谁？谁会因此受益，谁会因此承压？如果这两个问题讲清楚，视频就不会像新闻通稿，也不会像财经研报。

这里也要提醒一句，RSS 里没有的信息不要脑补，尤其是数字、当事方表态和时间线，最好二次核实。{fact_note}

如果你想看我继续跟进这件事，可以在评论区留下你的判断：你觉得它会变成大趋势，还是很快被市场忘掉？

目标字数：{words}

五、剪辑配图关键词
热点新闻截图、当事平台 Logo、时间线图、争议关键词、评论区反应、数据变化图

六、自检
【是否像新闻通稿】否
【是否有财经味】否
【前10秒是否有钩子】是
【是否适合普通用户】是
【是否存在事实不确定】是
【是否适合发布】中"""


async def generate_from_article(db: Session, article_id: int, duration: str, platform: str, use_llm: bool = True) -> dict:
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
    )
    record = ScriptGeneration(article_id=article.id, topic=None, duration=duration, platform=platform, script_text=text)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "article_id": article.id, "script_text": text}


async def generate_from_topic(db: Session, topic: str, duration: str, platform: str, use_llm: bool = True) -> dict:
    text = await generate_text(topic=topic, platform=platform, duration=duration, use_llm=use_llm)
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
) -> str:
    client = LLMClient()
    if use_llm and client.enabled:
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
            return await client.chat(prompt, temperature=0.75)
        except Exception:
            pass
    return fallback_script(topic, platform, duration, title, summary, source_name, link)

