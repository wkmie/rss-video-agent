from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    STREAMLIT_SECRETS = dict(st.secrets)
except Exception:
    STREAMLIT_SECRETS = {}

for key in (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DATABASE_URL",
    "RSS_MAX_ARTICLES_PER_SOURCE",
    "RSS_TIMEOUT_SECONDS",
):
    if key in STREAMLIT_SECRETS and key not in os.environ:
        os.environ[key] = str(STREAMLIT_SECRETS[key])

API_BASE = os.getenv("API_BASE_URL", "").rstrip("/")
USE_REMOTE_API = bool(API_BASE)
CATEGORIES = ["全部", "crypto_news", "bitcoin", "ai_news", "ai_research", "world_cup", "tech_news", "cybersecurity", "prediction_market"]
TIME_RANGES = ["最近 6 小时", "最近 12 小时", "最近 24 小时", "最近 3 天", "最近 7 天"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"]
PLATFORMS = ["视频号", "抖音", "小红书", "TikTok", "YouTube Shorts"]


st.set_page_config(page_title="RSS 视频选题助手", page_icon="RSS", layout="wide")
st.title("RSS 消息流筛选 + 短视频引流文案生成")


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
                )
            )
        raise ValueError(f"Unsupported direct path: {path}")
    finally:
        db.close()


def api_get(path: str, params: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(path, params=params)
    with httpx.Client(timeout=60) as client:
        response = client.get(f"{API_BASE}{path}", params=params)
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(path, payload=payload or {})
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{API_BASE}{path}", json=payload or {})
        response.raise_for_status()
        return response.json()


def ensure_state() -> None:
    st.session_state.setdefault("articles", [])
    st.session_state.setdefault("selected_article_id", None)
    st.session_state.setdefault("last_script", "")


def article_label(article: dict) -> str:
    title = article.get("title_zh") or article.get("title")
    return f"#{article['id']} | {article.get('score', 0):.0f}分 | {title}"


ensure_state()

tab_news, tab_script, tab_topic = st.tabs(["消息流获取", "文案生成", "主题直写"])

with tab_news:
    col1, col2, col3, col4 = st.columns([1.2, 1.4, 1.1, 1])
    with col1:
        category = st.selectbox("分类", CATEGORIES, index=0)
    with col2:
        keyword = st.text_input("关键词", placeholder="例如 bitcoin / AI / 世界杯")
    with col3:
        time_range = st.selectbox("时间范围", TIME_RANGES, index=2)
    with col4:
        limit = st.number_input("数量", min_value=5, max_value=50, value=10, step=5)

    action_col1, action_col2 = st.columns([1, 4])
    with action_col1:
        if st.button("抓取最新 RSS", use_container_width=True):
            with st.spinner("正在抓取 RSS..."):
                try:
                    result = api_post("/api/news/fetch")
                    st.success(f"抓取 {result['fetched']} 条，新增 {result['created']} 条，重复 {result['duplicates']} 条")
                    if result.get("errors"):
                        st.warning("\n".join(result["errors"]))
                except Exception as exc:
                    st.error(f"抓取失败：{exc}")
    with action_col2:
        if st.button("筛选选题", use_container_width=True):
            params = {
                "category": None if category == "全部" else category,
                "keyword": keyword or None,
                "time_range": time_range,
                "limit": int(limit),
            }
            with st.spinner("正在筛选..."):
                try:
                    st.session_state.articles = api_get("/api/news/topics", params=params)["items"]
                except Exception as exc:
                    st.error(f"筛选失败：{exc}")

    st.divider()
    if not st.session_state.articles:
        st.info("先点击“抓取最新 RSS”，再点击“筛选选题”。如果数据库已有文章，也可以直接筛选。")
    for article in st.session_state.articles:
        cols = st.columns([6, 1.5, 1.3])
        with cols[0]:
            st.subheader(article.get("title_zh") or article.get("title"))
            st.caption(
                f"{article.get('source_name')} | {article.get('category')} | "
                f"{article.get('published_at') or '未知时间'} | 推荐级别：{article.get('recommendation_level')}"
            )
            st.write(article.get("summary") or "")
            st.markdown(f"[原文链接]({article.get('link')})")
        with cols[1]:
            st.metric("热点评分", f"{article.get('score', 0):.0f}/100")
        with cols[2]:
            if st.button("生成文案", key=f"gen_{article['id']}", use_container_width=True):
                st.session_state.selected_article_id = article["id"]
                st.success("已选择该文章，请切到“文案生成”页面。")
            if st.button("选题分析", key=f"ana_{article['id']}", use_container_width=True):
                with st.spinner("正在分析选题..."):
                    try:
                        analysis = api_post("/api/news/analyze", {"article_id": article["id"], "use_llm": True})
                        st.json(analysis, expanded=False)
                    except Exception as exc:
                        st.error(f"分析失败：{exc}")
        st.divider()

with tab_script:
    articles = st.session_state.articles
    if articles:
        ids = [article["id"] for article in articles]
        default_index = ids.index(st.session_state.selected_article_id) if st.session_state.selected_article_id in ids else 0
        selected = st.selectbox("选择文章", articles, index=default_index, format_func=article_label)
        st.session_state.selected_article_id = selected["id"]
    else:
        selected_id = st.number_input("文章 ID", min_value=1, value=int(st.session_state.selected_article_id or 1))
        st.session_state.selected_article_id = int(selected_id)

    col1, col2 = st.columns(2)
    with col1:
        duration = st.selectbox("视频时长", DURATIONS, index=2)
    with col2:
        platform = st.selectbox("平台", PLATFORMS, index=1)

    if st.button("生成文章文案", type="primary"):
        with st.spinner("正在生成文案..."):
            try:
                result = api_post(
                    "/api/script/from_article",
                    {"article_id": st.session_state.selected_article_id, "duration": duration, "platform": platform, "use_llm": True},
                )
                st.session_state.last_script = result["script_text"]
            except Exception as exc:
                st.error(f"生成失败：{exc}")

    if st.session_state.last_script:
        st.text_area("生成结果", st.session_state.last_script, height=640)
        st.download_button("下载为 TXT", st.session_state.last_script, file_name="video_script.txt")

with tab_topic:
    topic = st.text_area("输入主题", placeholder="例如：AI Agent 会不会改变普通人的工作方式？", height=120)
    col1, col2 = st.columns(2)
    with col1:
        topic_duration = st.selectbox("视频时长 ", DURATIONS, index=2)
    with col2:
        topic_platform = st.selectbox("平台 ", PLATFORMS, index=1)

    if st.button("生成主题文案", type="primary"):
        if not topic.strip():
            st.warning("请先输入主题。")
        else:
            with st.spinner("正在生成主题文案..."):
                try:
                    result = api_post(
                        "/api/script/from_topic",
                        {"topic": topic.strip(), "duration": topic_duration, "platform": topic_platform, "use_llm": True},
                    )
                    st.session_state.topic_script = result["script_text"]
                except Exception as exc:
                    st.error(f"生成失败：{exc}")

    if st.session_state.get("topic_script"):
        st.text_area("主题文案结果", st.session_state.topic_script, height=640)
        st.download_button("下载主题文案 TXT", st.session_state.topic_script, file_name="topic_script.txt")
