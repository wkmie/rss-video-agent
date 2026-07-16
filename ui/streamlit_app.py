from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.auth import auth_headers, require_login

try:
    STREAMLIT_SECRETS = dict(st.secrets)
except Exception:
    STREAMLIT_SECRETS = {}

SECRET_ALIASES = {
    "OPENAI_API_KEY": ("OPENAI_API_KEY", "openai_api_key", "api_key"),
    "OPENAI_BASE_URL": ("OPENAI_BASE_URL", "openai_base_url", "base_url"),
    "OPENAI_MODEL": ("OPENAI_MODEL", "openai_model", "model"),
    "DATABASE_URL": ("DATABASE_URL", "database_url"),
    "RSS_MAX_ARTICLES_PER_SOURCE": ("RSS_MAX_ARTICLES_PER_SOURCE", "rss_max_articles_per_source"),
    "RSS_TIMEOUT_SECONDS": ("RSS_TIMEOUT_SECONDS", "rss_timeout_seconds"),
}


def streamlit_secret_value(env_key: str) -> Optional[str]:
    aliases = SECRET_ALIASES.get(env_key, (env_key,))
    for alias in aliases:
        if alias in STREAMLIT_SECRETS:
            return str(STREAMLIT_SECRETS[alias])
    for section_name in ("openai", "llm", "general", "app"):
        section = STREAMLIT_SECRETS.get(section_name)
        if isinstance(section, dict):
            for alias in aliases:
                if alias in section:
                    return str(section[alias])
    return None


for key in (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DATABASE_URL",
    "RSS_MAX_ARTICLES_PER_SOURCE",
    "RSS_TIMEOUT_SECONDS",
):
    value = streamlit_secret_value(key)
    if value and key not in os.environ:
        os.environ[key] = value

API_BASE = os.getenv("API_BASE_URL", "").rstrip("/")
USE_REMOTE_API = bool(API_BASE)
CATEGORIES = ["全部", "crypto", "ai", "tech"]
TIME_RANGES = ["最近 6 小时", "最近 12 小时", "最近 24 小时", "最近 3 天", "最近 7 天"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"]
PLATFORMS = ["视频号", "抖音", "小红书", "TikTok", "YouTube Shorts"]

TEXT = {
    "zh": {
        "lang_label": "语言",
        "title": "RSS 消息流筛选 + 短视频引流文案生成",
        "tab_news": "消息流获取",
        "tab_script": "文案生成",
        "tab_topic": "主题直写",
        "category": "分类",
        "keyword": "关键词",
        "keyword_placeholder": "例如 bitcoin / AI / 科技",
        "time_range": "时间范围",
        "limit": "数量",
        "fetch_rss": "抓取最新 RSS",
        "fetching": "正在抓取 RSS...",
        "fetch_success": "抓取 {fetched} 条，新增 {created} 条，重复 {duplicates} 条",
        "fetch_failed": "抓取失败：{error}",
        "filter_topics": "筛选选题",
        "filtering": "正在筛选...",
        "filter_failed": "筛选失败：{error}",
        "empty_articles": "先点击“抓取最新 RSS”，再点击“筛选选题”。如果数据库已有文章，也可以直接筛选。",
        "unknown_time": "未知时间",
        "recommendation": "推荐级别",
        "original_link": "原文链接",
        "score": "热点评分",
        "generate_script": "生成文案",
        "selected_article": "已选择该文章，请切到“文案生成”页面。",
        "analyze_topic": "选题分析",
        "analyzing": "正在分析选题...",
        "analysis_failed": "分析失败：{error}",
        "select_article": "选择文章",
        "article_id": "文章 ID",
        "duration": "视频时长",
        "platform": "平台",
        "generate_article_script": "生成文章文案",
        "generating": "正在生成文案...",
        "generation_failed": "生成失败：{error}",
        "generation_result": "生成结果",
        "download_txt": "下载为 TXT",
        "custom_generation": "自定义提示词生成（不包含视频标题、视频标签，如有需要请输入特定提示词）",
        "custom_article_caption": "自定义模式会把文章信息、平台和视频时长传给模型；结构和风格请写在自定义提示词里。",
        "custom_prompt": "自定义提示词",
        "custom_article_placeholder": "例如：生成一篇 90 秒抖音口播，用犀利观点型开头；面向币圈新手；不要硬广；结尾引导评论预测走势。",
        "generate_custom_article": "按自定义提示词生成文章文案",
        "missing_custom_prompt": "请先输入自定义提示词。",
        "custom_generating": "正在按自定义提示词生成文案...",
        "custom_result": "自定义提示词生成结果",
        "download_custom": "下载自定义文案 TXT",
        "topic_input": "输入主题",
        "topic_placeholder": "例如：AI Agent 会不会改变普通人的工作方式？",
        "generate_topic_script": "生成主题文案",
        "missing_topic": "请先输入主题。",
        "topic_generating": "正在生成主题文案...",
        "topic_result": "主题文案结果",
        "download_topic": "下载主题文案 TXT",
        "custom_topic_caption": "自定义模式会把主题信息、平台和视频时长传给模型；结构和风格请写在自定义提示词里。",
        "custom_topic_prompt": "主题自定义提示词",
        "custom_topic_placeholder": "例如：生成一篇 2 分钟小红书口播，用知识科普风格，先讲结论，再用 3 个例子展开；避免夸张标题党。",
        "generate_custom_topic": "按自定义提示词生成主题文案",
        "custom_topic_generating": "正在按自定义提示词生成主题文案...",
        "custom_topic_result": "主题自定义提示词生成结果",
        "download_custom_topic": "下载主题自定义文案 TXT",
        "points": "分",
        "all": "全部",
    },
    "en": {
        "lang_label": "Language",
        "title": "RSS Topic Discovery + Short Video Script Generator",
        "tab_news": "News Feed",
        "tab_script": "Script Generator",
        "tab_topic": "Topic Writer",
        "category": "Category",
        "keyword": "Keyword",
        "keyword_placeholder": "e.g. bitcoin / AI / tech",
        "time_range": "Time Range",
        "limit": "Limit",
        "fetch_rss": "Fetch Latest RSS",
        "fetching": "Fetching RSS...",
        "fetch_success": "Fetched {fetched}, created {created}, duplicates {duplicates}",
        "fetch_failed": "Fetch failed: {error}",
        "filter_topics": "Filter Topics",
        "filtering": "Filtering...",
        "filter_failed": "Filter failed: {error}",
        "empty_articles": "Click Fetch Latest RSS, then Filter Topics. If the database already has articles, you can filter directly.",
        "unknown_time": "Unknown time",
        "recommendation": "Recommendation",
        "original_link": "Original Link",
        "score": "Hotness Score",
        "generate_script": "Generate Script",
        "selected_article": "Article selected. Please switch to the Script Generator tab.",
        "analyze_topic": "Analyze Topic",
        "analyzing": "Analyzing topic...",
        "analysis_failed": "Analysis failed: {error}",
        "select_article": "Select Article",
        "article_id": "Article ID",
        "duration": "Video Duration",
        "platform": "Platform",
        "generate_article_script": "Generate Article Script",
        "generating": "Generating script...",
        "generation_failed": "Generation failed: {error}",
        "generation_result": "Generated Result",
        "download_txt": "Download TXT",
        "custom_generation": "Custom Prompt Generation (Video titles and tags are not included unless requested in your prompt.)",
        "custom_article_caption": "Custom mode sends article info, platform, and video duration to the model. Specify structure and style in your custom prompt.",
        "custom_prompt": "Custom Prompt",
        "custom_article_placeholder": "Example: Write a 90-second Douyin voiceover with a sharp opening, for crypto beginners, no hard sell, and end with a comment prompt.",
        "generate_custom_article": "Generate Article Script With Custom Prompt",
        "missing_custom_prompt": "Please enter a custom prompt first.",
        "custom_generating": "Generating with custom prompt...",
        "custom_result": "Custom Prompt Result",
        "download_custom": "Download Custom TXT",
        "topic_input": "Topic",
        "topic_placeholder": "e.g. Will AI agents change how ordinary people work?",
        "generate_topic_script": "Generate Topic Script",
        "missing_topic": "Please enter a topic first.",
        "topic_generating": "Generating topic script...",
        "topic_result": "Topic Script Result",
        "download_topic": "Download Topic TXT",
        "custom_topic_caption": "Custom mode sends topic info, platform, and video duration to the model. Specify structure and style in your custom prompt.",
        "custom_topic_prompt": "Topic Custom Prompt",
        "custom_topic_placeholder": "Example: Write a 2-minute Xiaohongshu voiceover in an educational style, start with the conclusion, then explain with 3 examples.",
        "generate_custom_topic": "Generate Topic Script With Custom Prompt",
        "custom_topic_generating": "Generating topic script with custom prompt...",
        "custom_topic_result": "Topic Custom Prompt Result",
        "download_custom_topic": "Download Topic Custom TXT",
        "points": "pts",
        "all": "All",
    },
}

CATEGORY_LABELS = {
    "zh": {
        "全部": "全部",
        "crypto": "加密货币",
        "ai": "人工智能",
        "tech": "科技新闻",
    },
    "en": {
        "全部": "All",
        "crypto": "Crypto",
        "ai": "Artificial Intelligence",
        "tech": "Tech News",
    }
}

TIME_RANGE_LABELS = {
    "en": {
        "最近 6 小时": "Last 6 hours",
        "最近 12 小时": "Last 12 hours",
        "最近 24 小时": "Last 24 hours",
        "最近 3 天": "Last 3 days",
        "最近 7 天": "Last 7 days",
    }
}

DURATION_LABELS = {
    "en": {
        "30秒": "30 sec",
        "1分钟": "1 min",
        "3分钟": "3 min",
        "5分钟": "5 min",
        "10分钟": "10 min",
    }
}


st.set_page_config(page_title="RSS Video Agent", page_icon="RSS", layout="wide")
require_login()


@st.cache_resource
def setup_direct_mode():
    from app.db.database import SessionLocal, init_db

    init_db()
    return SessionLocal


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


def direct_call(path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    from app.services.news_service import analyze_article, fetch_and_store, top_topic_pool
    from app.services.script_service import generate_from_article, generate_from_topic

    SessionLocal = setup_direct_mode()
    db = SessionLocal()
    try:
        if path == "/api/news/fetch":
            return run_async(fetch_and_store(db))
        if path == "/api/news/topics":
            params = params or {}
            return {
                "items": top_topic_pool(
                    db,
                    params.get("category"),
                    params.get("keyword"),
                    params.get("time_range"),
                    int(params.get("limit") or 10),
                )
            }
        if path == "/api/news/analyze":
            payload = payload or {}
            return run_async(analyze_article(db, int(payload["article_id"]), bool(payload.get("use_llm", True))))
        if path == "/api/script/from_article":
            payload = payload or {}
            return run_async(
                generate_from_article(
                    db,
                    int(payload["article_id"]),
                    payload.get("duration", "3分钟"),
                    payload.get("platform", "抖音"),
                    bool(payload.get("use_llm", True)),
                    payload.get("custom_prompt", ""),
                )
            )
        if path == "/api/script/from_topic":
            payload = payload or {}
            return run_async(
                generate_from_topic(
                    db,
                    payload.get("topic", ""),
                    payload.get("duration", "3分钟"),
                    payload.get("platform", "抖音"),
                    bool(payload.get("use_llm", True)),
                    payload.get("custom_prompt", ""),
                )
            )
        raise ValueError(f"Unsupported direct path: {path}")
    finally:
        db.close()


def api_get(path: str, params: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(path, params=params)
    with httpx.Client(timeout=60) as client:
        response = client.get(f"{API_BASE}{path}", params=params, headers=auth_headers())
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(path, payload=payload or {})
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{API_BASE}{path}", json=payload or {}, headers=auth_headers())
        response.raise_for_status()
        return response.json()


def ensure_state() -> None:
    st.session_state.setdefault("language", "zh")
    st.session_state.setdefault("articles", [])
    st.session_state.setdefault("selected_article_id", None)
    st.session_state.setdefault("last_script", "")
    st.session_state.setdefault("custom_script", "")
    st.session_state.setdefault("topic_custom_script", "")


ensure_state()
LANG = st.session_state.language


def t(key: str, **kwargs) -> str:
    text = TEXT[LANG].get(key, TEXT["zh"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(LANG, {}).get(value, value)


def time_range_label(value: str) -> str:
    return TIME_RANGE_LABELS.get(LANG, {}).get(value, value)


def duration_label(value: str) -> str:
    return DURATION_LABELS.get(LANG, {}).get(value, value)


def parse_content_package(value: str) -> Optional[dict]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    required_keys = {"video_titles", "cover_titles", "video_tags", "script"}
    return data if required_keys.issubset(data.keys()) else None


def render_content_package(label: str, value: str, download_key: str, file_name: str) -> None:
    package = parse_content_package(value)
    if not package:
        st.text_area(label, value, height=640)
        st.download_button(t("download_txt"), value, file_name=file_name, key=download_key)
        return

    st.subheader(label)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**视频标题**")
        for title in package.get("video_titles", []):
            st.write(f"- {title}")
    with col2:
        st.markdown("**封面标题**")
        for title in package.get("cover_titles", []):
            st.write(f"- {title}")

    tags = package.get("video_tags", [])
    if tags:
        st.markdown("**视频标签**")
        st.write(" ".join(str(tag) for tag in tags))

    st.text_area("视频文案", str(package.get("script", "")), height=520)
    st.download_button(t("download_txt"), value, file_name=file_name, key=download_key)


def article_label(article: dict) -> str:
    title = article.get("title_zh") or article.get("title")
    return f"#{article['id']} | {article.get('score', 0):.0f}{t('points')} | {title}"


title_col, lang_col = st.columns([5, 1])
with title_col:
    st.title(t("title"))
with lang_col:
    selected_language = st.selectbox(
        t("lang_label"),
        ["zh", "en"],
        index=["zh", "en"].index(st.session_state.language),
        format_func=lambda code: "中文" if code == "zh" else "English",
        key="language_selector",
    )
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        st.rerun()

LANG = st.session_state.language

tab_news, tab_script, tab_topic = st.tabs([t("tab_news"), t("tab_script"), t("tab_topic")])

with tab_news:
    col1, col2, col3, col4 = st.columns([1.2, 1.4, 1.1, 1])
    with col1:
        category = st.selectbox(t("category"), CATEGORIES, index=0, format_func=category_label)
    with col2:
        keyword = st.text_input(t("keyword"), placeholder=t("keyword_placeholder"))
    with col3:
        time_range = st.selectbox(t("time_range"), TIME_RANGES, index=2, format_func=time_range_label)
    with col4:
        limit = st.number_input(t("limit"), min_value=5, max_value=50, value=10, step=5)

    action_col1, action_col2 = st.columns([1, 4])
    with action_col1:
        if st.button(t("fetch_rss"), use_container_width=True):
            with st.spinner(t("fetching")):
                try:
                    result = api_post("/api/news/fetch")
                    st.success(t("fetch_success", fetched=result["fetched"], created=result["created"], duplicates=result["duplicates"]))
                    if result.get("errors"):
                        st.warning("\n".join(result["errors"]))
                except Exception as exc:
                    st.error(t("fetch_failed", error=exc))
    with action_col2:
        if st.button(t("filter_topics"), use_container_width=True):
            params = {
                "category": None if category == "全部" else category,
                "keyword": keyword or None,
                "time_range": time_range,
                "limit": int(limit),
            }
            with st.spinner(t("filtering")):
                try:
                    st.session_state.articles = api_get("/api/news/topics", params=params)["items"]
                except Exception as exc:
                    st.error(t("filter_failed", error=exc))

    st.divider()
    if not st.session_state.articles:
        st.info(t("empty_articles"))
    for article in st.session_state.articles:
        cols = st.columns([6, 1.5, 1.3])
        with cols[0]:
            st.subheader(article.get("title_zh") or article.get("title"))
            st.caption(
                f"{article.get('source_name')} | {article.get('category')} | "
                f"{article.get('published_at') or t('unknown_time')} | {t('recommendation')}：{article.get('recommendation_level')}"
            )
            st.write(article.get("summary") or "")
            st.markdown(f"[{t('original_link')}]({article.get('link')})")
        with cols[1]:
            st.metric(t("score"), f"{article.get('score', 0):.0f}/100")
        with cols[2]:
            if st.button(t("generate_script"), key=f"gen_{article['id']}", use_container_width=True):
                st.session_state.selected_article_id = article["id"]
                st.success(t("selected_article"))
            if st.button(t("analyze_topic"), key=f"ana_{article['id']}", use_container_width=True):
                with st.spinner(t("analyzing")):
                    try:
                        analysis = api_post("/api/news/analyze", {"article_id": article["id"], "use_llm": True})
                        st.json(analysis, expanded=False)
                    except Exception as exc:
                        st.error(t("analysis_failed", error=exc))
        st.divider()

with tab_script:
    articles = st.session_state.articles
    if articles:
        ids = [article["id"] for article in articles]
        default_index = ids.index(st.session_state.selected_article_id) if st.session_state.selected_article_id in ids else 0
        selected = st.selectbox(t("select_article"), articles, index=default_index, format_func=article_label)
        st.session_state.selected_article_id = selected["id"]
    else:
        selected_id = st.number_input(t("article_id"), min_value=1, value=int(st.session_state.selected_article_id or 1))
        st.session_state.selected_article_id = int(selected_id)

    col1, col2 = st.columns(2)
    with col1:
        duration = st.selectbox(t("duration"), DURATIONS, index=2, format_func=duration_label)
    with col2:
        platform = st.selectbox(t("platform"), PLATFORMS, index=1)

    if st.button(t("generate_article_script"), type="primary"):
        with st.spinner(t("generating")):
            try:
                result = api_post(
                    "/api/script/from_article",
                    {"article_id": st.session_state.selected_article_id, "duration": duration, "platform": platform, "use_llm": True},
                )
                st.session_state.last_script = result["script_text"]
            except Exception as exc:
                st.error(t("generation_failed", error=exc))

    if st.session_state.last_script:
        render_content_package(t("generation_result"), st.session_state.last_script, "download_article_default", "video_content_package.txt")

    st.divider()
    st.subheader(t("custom_generation"))
    st.caption(t("custom_article_caption"))
    custom_prompt = st.text_area(
        t("custom_prompt"),
        placeholder=t("custom_article_placeholder"),
        height=140,
        key="article_custom_prompt",
    )
    if st.button(t("generate_custom_article")):
        if not custom_prompt.strip():
            st.warning(t("missing_custom_prompt"))
        else:
            with st.spinner(t("custom_generating")):
                try:
                    result = api_post(
                        "/api/script/from_article",
                        {
                            "article_id": st.session_state.selected_article_id,
                            "duration": duration,
                            "platform": platform,
                            "use_llm": True,
                            "custom_prompt": custom_prompt.strip(),
                        },
                    )
                    st.session_state.custom_script = result["script_text"]
                except Exception as exc:
                    st.error(t("generation_failed", error=exc))

    if st.session_state.custom_script:
        st.text_area(t("custom_result"), st.session_state.custom_script, height=640)
        st.download_button(
            t("download_custom"),
            st.session_state.custom_script,
            file_name="custom_video_script.txt",
            key="download_article_custom",
        )

with tab_topic:
    topic = st.text_area(t("topic_input"), placeholder=t("topic_placeholder"), height=120)
    col1, col2 = st.columns(2)
    with col1:
        topic_duration = st.selectbox(t("duration"), DURATIONS, index=2, format_func=duration_label, key="topic_duration")
    with col2:
        topic_platform = st.selectbox(t("platform"), PLATFORMS, index=1, key="topic_platform")

    if st.button(t("generate_topic_script"), type="primary"):
        if not topic.strip():
            st.warning(t("missing_topic"))
        else:
            with st.spinner(t("topic_generating")):
                try:
                    result = api_post(
                        "/api/script/from_topic",
                        {"topic": topic.strip(), "duration": topic_duration, "platform": topic_platform, "use_llm": True},
                    )
                    st.session_state.topic_script = result["script_text"]
                except Exception as exc:
                    st.error(t("generation_failed", error=exc))

    if st.session_state.get("topic_script"):
        render_content_package(t("topic_result"), st.session_state.topic_script, "download_topic_default", "topic_content_package.txt")

    st.divider()
    st.subheader(t("custom_generation"))
    st.caption(t("custom_topic_caption"))
    topic_custom_prompt = st.text_area(
        t("custom_topic_prompt"),
        placeholder=t("custom_topic_placeholder"),
        height=140,
        key="topic_custom_prompt",
    )
    if st.button(t("generate_custom_topic")):
        if not topic.strip():
            st.warning(t("missing_topic"))
        elif not topic_custom_prompt.strip():
            st.warning(t("missing_custom_prompt"))
        else:
            with st.spinner(t("custom_topic_generating")):
                try:
                    result = api_post(
                        "/api/script/from_topic",
                        {
                            "topic": topic.strip(),
                            "duration": topic_duration,
                            "platform": topic_platform,
                            "use_llm": True,
                            "custom_prompt": topic_custom_prompt.strip(),
                        },
                    )
                    st.session_state.topic_custom_script = result["script_text"]
                except Exception as exc:
                    st.error(t("generation_failed", error=exc))

    if st.session_state.topic_custom_script:
        st.text_area(t("custom_topic_result"), st.session_state.topic_custom_script, height=640)
        st.download_button(
            t("download_custom_topic"),
            st.session_state.topic_custom_script,
            file_name="custom_topic_script.txt",
            key="download_topic_custom",
        )
