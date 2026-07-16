from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.auth import auth_headers, require_login

try:
    STREAMLIT_SECRETS = dict(st.secrets)
except Exception:
    STREAMLIT_SECRETS = {}

for key in (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DATABASE_URL",
    "X_BEARER_TOKEN",
    "LUNARCRUSH_API_KEY",
    "WEB3_HOT_REFRESH_SECONDS",
    "WEB3_HOT_ITEM_TTL_HOURS",
    "WEB3_HOT_MAX_ITEMS_PER_SOURCE",
):
    if key in STREAMLIT_SECRETS and key not in os.environ:
        os.environ[key] = str(STREAMLIT_SECRETS[key])


API_BASE = os.getenv("API_BASE_URL", "").rstrip("/")
USE_REMOTE_API = bool(API_BASE)
HEAT_LEVELS = ["全部", "red", "yellow", "gray"]
TREND_STATUS = ["全部", "new", "rising", "hot", "cooling"]
SOURCE_TYPES = ["全部", "rss", "google_news_rss", "x_recent_search", "lunarcrush"]
HOUR_OPTIONS = {"1小时": 1, "6小时": 6, "12小时": 12, "24小时": 24}
PLATFORMS = ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟"]


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


def setup_direct_mode():
    from app.db.database import SessionLocal, init_db

    init_db()
    return SessionLocal


def direct_call(method: str, path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    from app.services.web3_hot_service import (
        fetch_and_store_hot_items,
        generate_hot_content,
        generate_script_from_x_posts,
        get_hot_item_detail,
        hot_stats,
        list_hot_items,
        ticker_items,
    )

    SessionLocal = setup_direct_mode()
    db = SessionLocal()
    try:
        if method == "POST" and path == "/api/web3-hot/fetch-now":
            payload = payload or {}
            return run_async(fetch_and_store_hot_items(db, payload.get("source_type"), payload.get("keyword")))
        if method == "GET" and path == "/api/web3-hot/list":
            params = params or {}
            return {
                "items": list_hot_items(
                    db,
                    limit=int(params.get("limit") or 30),
                    heat_level=params.get("heat_level"),
                    trend_status=params.get("trend_status"),
                    keyword=params.get("keyword"),
                    source_type=params.get("source_type"),
                    hours=int(params.get("hours") or 24),
                )
            }
        if method == "GET" and path == "/api/web3-hot/ticker":
            params = params or {}
            return {"items": ticker_items(db, int(params.get("limit") or 15))}
        if method == "GET" and path == "/api/web3-hot/stats":
            return hot_stats(db)
        if method == "POST" and path == "/api/web3-hot/generate-from-x-posts":
            payload = payload or {}
            return run_async(
                generate_script_from_x_posts(
                    posts=payload.get("posts") or [],
                    target_platform=payload.get("target_platform", "抖音"),
                    duration=payload.get("duration", "3分钟"),
                    user_instruction=payload.get("user_instruction", ""),
                )
            )
        if method == "GET" and path.startswith("/api/web3-hot/"):
            return get_hot_item_detail(db, int(path.rsplit("/", 1)[-1]))
        if method == "POST" and path.endswith("/generate-content"):
            item_id = int(path.split("/")[-2])
            payload = payload or {}
            return run_async(
                generate_hot_content(
                    db,
                    item_id,
                    target_platform=payload.get("target_platform", "抖音"),
                    duration=payload.get("duration", "3分钟"),
                    user_instruction=payload.get("user_instruction", ""),
                    use_llm=bool(payload.get("use_llm", True)),
                )
            )
        raise ValueError(f"Unsupported direct call: {method} {path}")
    finally:
        db.close()


def api_request(method: str, path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(method, path, payload, params)
    with httpx.Client(timeout=180) as client:
        response = client.request(method, f"{API_BASE}{path}", json=payload, params=params, headers=auth_headers())
        response.raise_for_status()
        return response.json()


def format_time(value: Optional[str]) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        return value


def badge_style(level: str) -> str:
    return {
        "red": "background:#ffe5e5;color:#b00020;border:1px solid #ffb3b3;",
        "yellow": "background:#fff6d8;color:#8a6100;border:1px solid #ffe28a;",
        "gray": "background:#f1f3f5;color:#495057;border:1px solid #dee2e6;",
    }.get(level, "background:#f1f3f5;color:#495057;border:1px solid #dee2e6;")


def group_items_by_source(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        source_name = item.get("source_name") or "未知消息源"
        grouped.setdefault(source_name, []).append(item)
    return grouped


def render_generated_content(content: dict) -> str:
    text = f"""【视频标题】
{chr(10).join(content.get("video_titles") or [])}

【封面标题】
{chr(10).join(content.get("cover_titles") or [])}

【视频标签】
{" ".join(content.get("video_tags") or [])}

【完整口播文案】
{content.get("script", "")}
"""
    st.text_area("生成结果", text, height=620)
    return text


st.set_page_config(page_title="Web3 实时热度消息墙", page_icon="🔥", layout="wide")
require_login()
st.title("Web3 实时热度消息墙")
st.caption("聚合 Web3 / Crypto 新闻、Google News、可选 X 与 LunarCrush 信号，按热度排序展示正在发酵的消息。")

refresh_seconds = int(os.getenv("WEB3_HOT_REFRESH_SECONDS", "60") or 60)
auto_refresh = st.toggle("自动刷新页面", value=True)


@st.fragment(run_every=refresh_seconds if auto_refresh else None)
def schedule_session_safe_refresh() -> None:
    if not auto_refresh:
        st.session_state.pop("web3_hot_last_app_refresh", None)
        return

    now = time.monotonic()
    last_refresh = st.session_state.get("web3_hot_last_app_refresh")
    if last_refresh is None:
        st.session_state.web3_hot_last_app_refresh = now
        return
    if now - last_refresh >= max(refresh_seconds - 1, 1):
        st.session_state.web3_hot_last_app_refresh = now
        st.rerun(scope="app")


schedule_session_safe_refresh()

st.session_state.setdefault("web3_hot_items", [])
st.session_state.setdefault("web3_hot_selected_id", None)
st.session_state.setdefault("web3_hot_generated", None)
st.session_state.setdefault("web3_x_posts_script", "")

try:
    stats = api_request("GET", "/api/web3-hot/stats")
except Exception as exc:
    stats = {}
    st.warning(f"统计信息读取失败：{exc}")

top_cols = st.columns(7)
top_cols[0].metric("当前时间", datetime.now().strftime("%H:%M:%S"))
top_cols[1].metric("最近刷新", format_time(stats.get("latest_refresh_time")))
top_cols[2].metric("今日抓取", stats.get("today_count", 0))
top_cols[3].metric("Red", stats.get("red_count", 0))
top_cols[4].metric("Yellow", stats.get("yellow_count", 0))
top_cols[5].metric("启用源", stats.get("enabled_source_count", 0))
top_cols[6].metric("X/LC", f"{'X' if stats.get('x_configured') else '-'} / {'LC' if stats.get('lunarcrush_configured') else '-'}")

st.divider()
with st.expander("粘贴 X 消息生成文案", expanded=False):
    x_post_count = int(st.number_input("X 消息数量", min_value=1, max_value=20, value=1, step=1))
    x_posts = [
        st.text_area(
            f"X 消息 {index}",
            key=f"manual_x_post_{index}",
            height=120,
            placeholder="粘贴 X 帖子正文，也可同时包含作者、时间和链接",
        )
        for index in range(1, x_post_count + 1)
    ]

    x_gen_cols = st.columns([1, 1, 2])
    with x_gen_cols[0]:
        x_platform = st.selectbox("目标平台", PLATFORMS, key="manual_x_platform")
    with x_gen_cols[1]:
        x_duration = st.selectbox("视频时长", DURATIONS, index=2, key="manual_x_duration")
    with x_gen_cols[2]:
        x_instruction = st.text_input(
            "补充要求",
            key="manual_x_instruction",
            placeholder="例如：强调消息之间的冲突，保持中立",
        )

    if st.button("根据 X 消息生成文案", type="primary", key="generate_manual_x_script"):
        normalized_x_posts = [post.strip() for post in x_posts if post.strip()]
        if not normalized_x_posts:
            st.warning("请至少输入一条 X 消息")
        else:
            with st.spinner("正在综合 X 消息并生成文案..."):
                try:
                    result = api_request(
                        "POST",
                        "/api/web3-hot/generate-from-x-posts",
                        {
                            "posts": normalized_x_posts,
                            "target_platform": x_platform,
                            "duration": x_duration,
                            "user_instruction": x_instruction,
                        },
                    )
                    st.session_state.web3_x_posts_script = result.get("script", "")
                except Exception as exc:
                    st.error(f"生成失败：{exc}")

    if st.session_state.web3_x_posts_script:
        st.text_area("X 消息文案", st.session_state.web3_x_posts_script, height=520)
        st.download_button(
            "下载文案",
            st.session_state.web3_x_posts_script,
            file_name="x_posts_script.txt",
            mime="text/plain",
            key="download_manual_x_script",
        )

st.divider()
st.subheader("抓取与筛选")
filter_cols = st.columns([1.1, 1.1, 1.1, 1.4, 1.4, 0.9, 1.1])
with filter_cols[0]:
    hours_label = st.selectbox("时间范围", list(HOUR_OPTIONS.keys()), index=3)
with filter_cols[1]:
    heat_level = st.selectbox("热度等级", HEAT_LEVELS)
with filter_cols[2]:
    trend_status = st.selectbox("趋势状态", TREND_STATUS)
with filter_cols[3]:
    source_type = st.selectbox("数据源类型", SOURCE_TYPES)
with filter_cols[4]:
    keyword = st.text_input("关键词", placeholder="BTC / ETF / hack / Strategy")
with filter_cols[5]:
    limit = st.number_input("数量", min_value=10, max_value=100, value=30, step=10)
with filter_cols[6]:
    fetch_source = st.selectbox("抓取源", ["全部", "rss", "google_news_rss", "x_recent_search", "lunarcrush"])

action_cols = st.columns([1.2, 1.2, 5])
if action_cols[0].button("立即刷新", type="primary", use_container_width=True):
    with st.spinner("正在抓取 Web3 热点..."):
        try:
            result = api_request(
                "POST",
                "/api/web3-hot/fetch-now",
                {
                    "source_type": None if fetch_source == "全部" else fetch_source,
                    "keyword": keyword or None,
                },
            )
            st.success(
                f"抓取 {result['fetched_count']} 条，新增 {result['inserted_count']} 条，更新 {result['updated_count']} 条，跳过 {result['skipped_count']} 条"
            )
            if result.get("errors"):
                st.warning("\n".join(result["errors"]))
        except Exception as exc:
            st.error(f"抓取失败：{exc}")

if action_cols[1].button("查询热点", use_container_width=True):
    try:
        st.session_state.web3_hot_items = api_request(
            "GET",
            "/api/web3-hot/list",
            params={
                "limit": int(limit),
                "heat_level": None if heat_level == "全部" else heat_level,
                "trend_status": None if trend_status == "全部" else trend_status,
                "source_type": None if source_type == "全部" else source_type,
                "keyword": keyword or None,
                "hours": HOUR_OPTIONS[hours_label],
            },
        )["items"]
    except Exception as exc:
        st.error(f"查询失败：{exc}")

if not st.session_state.web3_hot_items:
    try:
        st.session_state.web3_hot_items = api_request("GET", "/api/web3-hot/list", params={"limit": int(limit), "hours": HOUR_OPTIONS[hours_label]})["items"]
    except Exception:
        st.session_state.web3_hot_items = []

items = st.session_state.web3_hot_items

st.divider()
grouped_items = group_items_by_source(items)
st.subheader(f"按消息源展示（{len(grouped_items)} 个消息源，{len(items)} 条消息）")
if not items:
    st.info("暂无热点。点击“立即刷新”抓取最新 Web3 消息。")
else:
    for source_name, source_items in grouped_items.items():
        with st.expander(f"{source_name}（{len(source_items)} 条）", expanded=True):
            for source_index, item in enumerate(source_items, start=1):
                cols = st.columns([0.45, 0.85, 0.85, 0.9, 4.6, 1.3])
                cols[0].write(source_index)
                cols[1].markdown(
                    f"<span style='{badge_style(item.get('heat_level', 'gray'))}border-radius:999px;padding:2px 8px'>"
                    f"{item.get('heat_level')}</span>",
                    unsafe_allow_html=True,
                )
                cols[2].write(item.get("trend_status"))
                cols[3].write(f"{item.get('heat_score', 0):.1f}")
                cols[4].markdown(f"**{item.get('title')}**")
                cols[4].caption(" ".join(item.get("matched_keywords") or []))
                cols[5].write(format_time(item.get("published_at")))

                item_actions = st.columns([1, 1.2, 0.8, 5])
                if item_actions[0].button("查看详情", key=f"hot_detail_{item['id']}"):
                    st.session_state.web3_hot_selected_id = item["id"]
                if item_actions[1].button("生成视频内容", key=f"hot_generate_select_{item['id']}"):
                    st.session_state.web3_hot_selected_id = item["id"]
                    st.session_state.web3_hot_generated = None
                if item.get("link"):
                    item_actions[2].link_button("来源", item["link"])
                if source_index < len(source_items):
                    st.divider()

selected_id = st.session_state.web3_hot_selected_id
if selected_id:
    st.subheader("热点详情")
    try:
        detail = api_request("GET", f"/api/web3-hot/{selected_id}")
        dcols = st.columns([2.5, 1, 1, 1])
        dcols[0].markdown(f"**{detail.get('title')}**")
        dcols[1].metric("热度分", f"{detail.get('heat_score', 0):.1f}")
        dcols[2].metric("热度等级", detail.get("heat_level", "gray"))
        dcols[3].metric("趋势", detail.get("trend_status", "new"))
        st.write(detail.get("summary") or detail.get("content") or "")
        st.caption(f"来源：{detail.get('source_name')} | 类型：{detail.get('source_type')} | 发布时间：{format_time(detail.get('published_at'))}")
        st.write("命中关键词：", " ".join(detail.get("matched_keywords") or []) or "-")
        st.write("多源确认：", len(detail.get("related_sources") or []), "条")
        st.write("可能是传言：", "是，需要进一步确认" if detail.get("is_rumor_like") else "否")
        st.write("适合立刻生成视频：", "是" if detail.get("suitable_for_video_now") else "建议先核实")
        with st.expander("热度评分详情"):
            st.json(detail.get("score_detail") or {})
        if detail.get("related_sources"):
            with st.expander("相关来源"):
                for related in detail["related_sources"]:
                    st.markdown(f"- [{related.get('source_name')}]({related.get('link') or '#'})：{related.get('title')}")
    except Exception as exc:
        st.error(f"详情读取失败：{exc}")
        detail = None

    st.subheader("内容生成")
    gen_cols = st.columns([1, 1, 2, 1])
    with gen_cols[0]:
        platform = st.selectbox("目标平台", PLATFORMS)
    with gen_cols[1]:
        duration = st.selectbox("视频时长", DURATIONS, index=2)
    with gen_cols[2]:
        user_instruction = st.text_input("补充要求", placeholder="例如：更适合视频号，强调风险，不要投资建议")
    with gen_cols[3]:
        use_llm = st.checkbox("使用 LLM", value=True)

    if st.button("生成热点视频内容", type="primary"):
        with st.spinner("正在生成内容..."):
            try:
                st.session_state.web3_hot_generated = api_request(
                    "POST",
                    f"/api/web3-hot/{selected_id}/generate-content",
                    {
                        "target_platform": platform,
                        "duration": duration,
                        "user_instruction": user_instruction,
                        "use_llm": use_llm,
                    },
                )
            except Exception as exc:
                st.error(f"生成失败：{exc}")

    if st.session_state.web3_hot_generated:
        output = render_generated_content(st.session_state.web3_hot_generated)
        st.download_button("下载结果", output, file_name=f"web3_hot_content_{selected_id}.txt", mime="text/plain")
