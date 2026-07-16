from __future__ import annotations

import asyncio
import json
import os
import sys
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

for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "DATABASE_URL"):
    if key in STREAMLIT_SECRETS and key not in os.environ:
        os.environ[key] = str(STREAMLIT_SECRETS[key])


API_BASE = os.getenv("API_BASE_URL", "").rstrip("/")
USE_REMOTE_API = bool(API_BASE)
PLATFORMS = ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"]


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


def direct_generate(payload: dict) -> dict:
    from app.trading_cognition.service import generate_trading_cognition

    SessionLocal = setup_direct_mode()
    db = SessionLocal()
    try:
        return run_async(
            generate_trading_cognition(
                db,
                payload.get("question", ""),
                payload.get("duration", "1分钟"),
                payload.get("platform", "抖音"),
                bool(payload.get("use_llm", True)),
                int(payload.get("knowledge_limit") or 4),
            )
        )
    finally:
        db.close()


def generate_content(payload: dict) -> dict:
    if not USE_REMOTE_API:
        return direct_generate(payload)
    with httpx.Client(timeout=180) as client:
        response = client.post(
            f"{API_BASE}/api/trading-cognition/generate",
            json=payload,
            headers=auth_headers(),
        )
    if response.is_error:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(str(detail or f"HTTP {response.status_code}"))
    return response.json()


def parse_content_package(value: str) -> Optional[dict]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return None
    required = {"video_titles", "cover_titles", "video_tags", "script"}
    return data if isinstance(data, dict) and required.issubset(data) else None


def render_content_package(value: str) -> None:
    package = parse_content_package(value)
    if not package:
        st.text_area("生成结果", value, height=640)
        st.download_button("下载 TXT", value, file_name="trading_cognition_content_package.txt")
        return

    st.subheader("生成结果")
    title_col, cover_col = st.columns(2)
    with title_col:
        st.markdown("**视频标题**")
        for title in package.get("video_titles", []):
            st.write(f"- {title}")
    with cover_col:
        st.markdown("**封面标题**")
        for title in package.get("cover_titles", []):
            st.write(f"- {title}")

    tags = package.get("video_tags", [])
    if tags:
        st.markdown("**视频标签**")
        st.write(" ".join(str(tag) for tag in tags))
    st.text_area("完整口播文案", str(package.get("script", "")), height=520)
    st.download_button("下载内容包 TXT", value, file_name="trading_cognition_content_package.txt")


st.set_page_config(page_title="交易认知", page_icon="🧠", layout="wide")
require_login()

st.title("交易认知")
st.caption(
    "从“尼克｜交易性格”公开内容蒸馏出的认知库中检索相关依据，再生成交易认知口播。"
    "不提供具体品种、点位、买卖信号或收益承诺。"
)

st.session_state.setdefault("trading_page_script", "")
st.session_state.setdefault("trading_page_matches", [])
st.session_state.setdefault("trading_page_source_notice", "")

st.divider()
question = st.text_area(
    "输入交易认知问题",
    placeholder="例如：交易为什么要设置止损？",
    height=130,
    key="trading_page_question",
)

option_cols = st.columns(3)
with option_cols[0]:
    duration = st.selectbox("视频时长", DURATIONS, index=1)
with option_cols[1]:
    platform = st.selectbox("发布平台", PLATFORMS, index=0)
with option_cols[2]:
    use_llm = st.toggle("使用大模型生成", value=True, help="关闭后使用本地规则版，可用于离线验证。")

if st.button("生成交易认知文案", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("请先输入交易认知问题。")
    else:
        with st.spinner("正在检索认知资料并生成文案..."):
            try:
                result = generate_content(
                    {
                        "question": question.strip(),
                        "duration": duration,
                        "platform": platform,
                        "use_llm": use_llm,
                        "knowledge_limit": 4,
                    }
                )
                st.session_state.trading_page_script = result["script_text"]
                st.session_state.trading_page_matches = result.get("matched_knowledge", [])
                st.session_state.trading_page_source_notice = result.get("source_notice", "")
            except Exception as exc:
                st.error(f"生成失败：{exc}")

if st.session_state.trading_page_script:
    st.divider()
    render_content_package(st.session_state.trading_page_script)

    if st.session_state.trading_page_source_notice:
        st.caption(f"资料来源说明：{st.session_state.trading_page_source_notice}")

    matches = st.session_state.trading_page_matches
    if matches:
        with st.expander("本次采用的认知依据"):
            for card in matches:
                st.markdown(f"**{card.get('title', '')}**")
                st.write(card.get("belief", ""))
                if card.get("action_rule"):
                    st.caption(card["action_rule"])
