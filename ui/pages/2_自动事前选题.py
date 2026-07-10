from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
    "FINNHUB_API_KEY",
    "TRADING_ECONOMICS_API_KEY",
    "COINMARKETCAL_API_KEY",
    "TOKEN_UNLOCKS_API_KEY",
    "MESSARI_API_KEY",
):
    if key in STREAMLIT_SECRETS and key not in os.environ:
        os.environ[key] = str(STREAMLIT_SECRETS[key])


API_BASE = os.getenv("API_BASE_URL", "").rstrip("/")
USE_REMOTE_API = bool(API_BASE)

CATEGORIES = ["全部", "宏观数据", "Web3", "Token解锁", "AI科技", "网络安全", "监管", "其他"]
IMPORTANCE = ["全部", "medium", "high", "critical"]
STATUS = ["全部", "待生成", "已生成", "已审核", "已发布", "已放弃"]
TIME_RANGES = {"未来 24 小时": 1, "未来 3 天": 3, "未来 7 天": 7, "未来 30 天": 30}
PLATFORMS = ["视频号", "抖音", "小红书", "TikTok", "YouTube Shorts"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"]
STATUS_TO_API = {"待生成": "pending", "已生成": "topic_generated", "已审核": "reviewed", "已发布": "published", "已放弃": "abandoned"}


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


def parse_datetime_param(value):
    if not value or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def direct_call(method: str, path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    from app.services.pre_event_service import fetch_and_store_pre_events, list_pre_events, upcoming_events, update_event_status
    from app.services.pre_topic_service import generate_pre_topic, list_pre_topics, update_pre_topic_status

    SessionLocal = setup_direct_mode()
    db = SessionLocal()
    try:
        if method == "POST" and path == "/api/pre-events/fetch":
            payload = payload or {}
            return run_async(fetch_and_store_pre_events(db, int(payload.get("days") or 30), payload.get("categories"), bool(payload.get("force_refresh", False))))
        if method == "GET" and path == "/api/pre-events/list":
            params = params or {}
            return {
                "items": list_pre_events(
                    db,
                    category=params.get("category"),
                    importance_level=params.get("importance_level"),
                    status=params.get("status"),
                    keyword=params.get("keyword"),
                    limit=int(params.get("limit") or 100),
                    start_time=parse_datetime_param(params.get("start_time")),
                    end_time=parse_datetime_param(params.get("end_time")),
                )
            }
        if method == "GET" and path == "/api/pre-events/upcoming":
            params = params or {}
            return {"items": upcoming_events(db, int(params.get("days") or 7), params.get("category"), params.get("importance_level"))}
        if method == "POST" and path == "/api/pre-topics/generate":
            payload = payload or {}
            return run_async(generate_pre_topic(db, int(payload["event_id"]), payload.get("target_platform", "视频号"), payload.get("duration", "3分钟"), payload.get("user_instruction", ""), bool(payload.get("use_llm", True))))
        if method == "GET" and path == "/api/pre-topics/list":
            params = params or {}
            return {"items": list_pre_topics(db, params.get("status"), int(params.get("limit") or 100))}
        if method == "PUT" and path.startswith("/api/pre-topics/"):
            topic_id = int(path.split("/")[-2])
            return update_pre_topic_status(db, topic_id, (payload or {}).get("status", "reviewed"))
        if method == "PUT" and path.startswith("/api/pre-events/"):
            event_id = int(path.split("/")[-2])
            return update_event_status(db, event_id, (payload or {}).get("status", "reviewed"))
        raise ValueError(f"Unsupported direct call: {method} {path}")
    finally:
        db.close()


def api_request(method: str, path: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    if not USE_REMOTE_API:
        return direct_call(method, path, payload, params)
    with httpx.Client(timeout=120) as client:
        response = client.request(method, f"{API_BASE}{path}", json=payload, params=params)
        response.raise_for_status()
        return response.json()


def format_time(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def render_topic(topic: dict) -> str:
    tags = " ".join(topic.get("video_tags") or [])
    content = f"""【视频标题】
{topic.get("video_title", "")}

【封面标题】
{topic.get("cover_title", "")}

【视频标签】
{tags}

【选题理由】
{topic.get("topic_reason", "")}

【文案方向】
{topic.get("script_direction", "")}

【完整口播文案】
{topic.get("script", "")}

【建议发布时间】
{topic.get("suggested_publish_time", "")}
"""
    st.text_area("生成结果", content, height=720)
    return content


st.set_page_config(page_title="自动事前选题", page_icon="📅", layout="wide")
st.title("自动事前选题")
st.caption("从互联网自动抓取未来重要事件，并生成适合 KOL 提前发布的视频内容。")

st.session_state.setdefault("pre_events", [])
st.session_state.setdefault("selected_pre_event_id", None)
st.session_state.setdefault("last_pre_topic", None)

st.divider()
st.subheader("事件抓取")
fetch_buttons = [
    ("抓取未来 7 天事件", 7, None),
    ("抓取未来 30 天事件", 30, None),
    ("仅抓宏观数据", 30, ["宏观数据"]),
    ("仅抓 Web3 事件", 30, ["Web3"]),
    ("仅抓 Token 解锁", 30, ["Token解锁"]),
    ("仅抓 AI 科技事件", 30, ["AI科技"]),
    ("仅抓监管事件", 30, ["监管"]),
    ("仅抓网络安全事件", 30, ["网络安全"]),
]
fetch_cols = st.columns(4)
for index, (label, days, categories) in enumerate(fetch_buttons):
    col = fetch_cols[index % len(fetch_cols)]
    with col:
        if st.button(label, use_container_width=True):
            with st.spinner("正在抓取未来事件..."):
                try:
                    result = api_request("POST", "/api/pre-events/fetch", {"days": days, "categories": categories, "force_refresh": False})
                    st.success(
                        f"抓取 {result['fetched_count']} 条，新增 {result['inserted_count']} 条，更新 {result['updated_count']} 条，跳过 {result['skipped_count']} 条"
                    )
                    if result.get("errors"):
                        st.warning("\n".join(result["errors"]))
                except Exception as exc:
                    st.error(f"抓取失败：{exc}")

st.divider()
st.subheader("事件筛选")
filter_cols = st.columns([1.2, 1.1, 1.1, 1.1, 1.8, 0.9])
with filter_cols[0]:
    time_label = st.selectbox("时间范围", list(TIME_RANGES.keys()), index=2)
with filter_cols[1]:
    category = st.selectbox("分类", CATEGORIES)
with filter_cols[2]:
    importance = st.selectbox("重要性", IMPORTANCE)
with filter_cols[3]:
    status = st.selectbox("状态", STATUS)
with filter_cols[4]:
    keyword = st.text_input("关键词搜索", placeholder="例如 CPI / OpenAI / SEC / unlock")
with filter_cols[5]:
    limit = st.number_input("数量", min_value=10, max_value=200, value=50, step=10)

if st.button("筛选未来事件", type="primary"):
    now = datetime.now(timezone.utc)
    params = {
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(days=TIME_RANGES[time_label])).isoformat(),
        "category": None if category == "全部" else category,
        "importance_level": None if importance == "全部" else importance,
        "status": None if status == "全部" else status,
        "keyword": keyword or None,
        "limit": int(limit),
    }
    with st.spinner("正在查询事件..."):
        try:
            st.session_state.pre_events = api_request("GET", "/api/pre-events/list", params=params)["items"]
        except Exception as exc:
            st.error(f"查询失败：{exc}")

events = st.session_state.pre_events
if not events:
    st.info("先点击抓取按钮，再筛选未来事件。")
else:
    st.subheader(f"事件列表（{len(events)} 条）")
    for event in events:
        with st.container():
            cols = st.columns([0.7, 1.5, 3, 1, 1, 1, 1.2])
            cols[0].write(f"#{event['id']}")
            cols[1].write(format_time(event.get("event_time")))
            cols[2].markdown(f"**{event.get('event_name')}**")
            cols[2].caption(event.get("description") or "")
            cols[3].write(event.get("category"))
            cols[4].write(event.get("importance_level"))
            cols[5].write(f"{event.get('impact_score') or 0:.0f}")
            cols[6].write(event.get("source"))
            st.caption(f"国家/资产：{event.get('country') or event.get('asset_or_topic') or '-'} | 关键词：{' '.join(event.get('keywords') or [])} | 状态：{event.get('status')}")
            action_cols = st.columns([1, 1, 1, 1, 4])
            if action_cols[0].button("生成事前选题", key=f"select_pre_{event['id']}"):
                st.session_state.selected_pre_event_id = event["id"]
                st.success("已选择事件，请在下方生成内容。")
            if event.get("source_url"):
                action_cols[1].link_button("查看来源", event["source_url"])
            if action_cols[2].button("标记已审核", key=f"review_{event['id']}"):
                api_request("PUT", f"/api/pre-events/{event['id']}/status", {"status": "reviewed"})
                st.rerun()
            if action_cols[3].button("放弃", key=f"abandon_{event['id']}"):
                api_request("PUT", f"/api/pre-events/{event['id']}/status", {"status": "abandoned"})
                st.rerun()
            st.divider()

st.subheader("生成事前选题")
selected_id = st.number_input("事件 ID", min_value=1, value=int(st.session_state.selected_pre_event_id or 1))
gen_cols = st.columns([1, 1])
with gen_cols[0]:
    target_platform = st.selectbox("目标平台", PLATFORMS, index=0)
with gen_cols[1]:
    duration = st.selectbox("视频时长", DURATIONS, index=2)
user_instruction = st.text_area("用户补充要求", placeholder="例如：面向币圈新手，开头更犀利，结尾引导用户预测事件影响。", height=120)

if st.button("生成内容", type="primary"):
    with st.spinner("正在生成事前选题内容..."):
        try:
            st.session_state.last_pre_topic = api_request(
                "POST",
                "/api/pre-topics/generate",
                {
                    "event_id": int(selected_id),
                    "target_platform": target_platform,
                    "duration": duration,
                    "user_instruction": user_instruction,
                    "use_llm": True,
                },
            )
        except Exception as exc:
            st.error(f"生成失败：{exc}")

if st.session_state.last_pre_topic:
    content = render_topic(st.session_state.last_pre_topic)
    result_cols = st.columns([1, 1, 1, 4])
    if result_cols[0].button("标记已审核"):
        st.session_state.last_pre_topic = api_request("PUT", f"/api/pre-topics/{st.session_state.last_pre_topic['id']}/status", {"status": "reviewed"})
        st.success("已标记为已审核")
    if result_cols[1].button("标记已发布"):
        st.session_state.last_pre_topic = api_request("PUT", f"/api/pre-topics/{st.session_state.last_pre_topic['id']}/status", {"status": "published"})
        st.success("已标记为已发布")
    result_cols[2].download_button("复制/下载结果", content, file_name="pre_event_topic.txt")
