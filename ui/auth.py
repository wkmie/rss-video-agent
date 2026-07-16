from __future__ import annotations

import os
from typing import Optional

import httpx
import streamlit as st


def _api_base() -> str:
    return os.getenv("API_BASE_URL", "").rstrip("/")


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _direct_auth_request(method: str, path: str, payload: Optional[dict] = None) -> dict:
    from app.db.database import SessionLocal, init_db
    from app.services.auth_service import (
        authenticate_token,
        authenticate_user,
        change_password,
        create_session,
        create_user,
        revoke_session,
        user_payload,
    )

    init_db()
    db = SessionLocal()
    try:
        payload = payload or {}
        token = st.session_state.get("auth_token", "")
        if method == "POST" and path == "/api/auth/register":
            user = create_user(
                db,
                payload.get("username", ""),
                payload.get("email", ""),
                payload.get("password", ""),
                payload.get("display_name", ""),
            )
            return {"access_token": create_session(db, user), "token_type": "bearer", "user": user_payload(user)}
        if method == "POST" and path == "/api/auth/login":
            user = authenticate_user(db, payload.get("identifier", ""), payload.get("password", ""))
            return {"access_token": create_session(db, user), "token_type": "bearer", "user": user_payload(user)}

        user, _ = authenticate_token(db, token)
        if method == "GET" and path == "/api/auth/me":
            return user_payload(user)
        if method == "POST" and path == "/api/auth/logout":
            revoke_session(db, token)
            return {"ok": True}
        if method == "POST" and path == "/api/auth/change-password":
            new_token = change_password(
                db,
                user,
                payload.get("current_password", ""),
                payload.get("new_password", ""),
            )
            return {"access_token": new_token, "token_type": "bearer", "user": user_payload(user)}
        raise ValueError(f"Unsupported auth call: {method} {path}")
    finally:
        db.close()


def auth_request(method: str, path: str, payload: Optional[dict] = None) -> dict:
    api_base = _api_base()
    if not api_base:
        return _direct_auth_request(method, path, payload)

    with httpx.Client(timeout=30) as client:
        response = client.request(method, f"{api_base}{path}", json=payload, headers=auth_headers())
    if response.is_error:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(str(detail or f"HTTP {response.status_code}"))
    return response.json()


def _store_auth(result: dict) -> None:
    st.session_state.auth_token = result["access_token"]
    st.session_state.auth_user = result["user"]


def _clear_auth() -> None:
    for key in list(st.session_state.keys()):
        if key not in {"language", "language_selector"}:
            del st.session_state[key]


def _render_login_page() -> None:
    language = st.session_state.get("language", "zh")
    is_zh = language == "zh"
    left, center, right = st.columns([1, 1.35, 1])
    with center:
        selected_language = st.selectbox(
            "语言 / Language",
            ["zh", "en"],
            index=["zh", "en"].index(language),
            format_func=lambda value: "中文" if value == "zh" else "English",
            key="auth_language_selector",
        )
        if selected_language != language:
            st.session_state.language = selected_language
            st.rerun()
        st.title("RSS Video Agent")
        st.caption("登录后使用消息采集、选题分析和文案生成功能" if is_zh else "Sign in to access news collection and content generation")
        login_tab, register_tab = st.tabs(["登录" if is_zh else "Sign in", "注册账号" if is_zh else "Create account"])

        with login_tab:
            with st.form("login_form"):
                identifier = st.text_input("用户名或邮箱" if is_zh else "Username or email")
                password = st.text_input("密码" if is_zh else "Password", type="password")
                submitted = st.form_submit_button("登录" if is_zh else "Sign in", type="primary", use_container_width=True)
            if submitted:
                if not identifier.strip() or not password:
                    st.warning("请输入用户名和密码" if is_zh else "Enter your username and password")
                else:
                    try:
                        _store_auth(auth_request("POST", "/api/auth/login", {"identifier": identifier, "password": password}))
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        with register_tab:
            with st.form("register_form"):
                username = st.text_input("用户名" if is_zh else "Username", help="3-32 位字母、数字或下划线")
                email = st.text_input("邮箱" if is_zh else "Email")
                display_name = st.text_input("显示名称（选填）" if is_zh else "Display name (optional)")
                password = st.text_input("设置密码" if is_zh else "Password", type="password", help="至少 8 位，并同时包含字母和数字")
                password_confirm = st.text_input("确认密码" if is_zh else "Confirm password", type="password")
                submitted = st.form_submit_button("注册并登录" if is_zh else "Create account", type="primary", use_container_width=True)
            if submitted:
                if password != password_confirm:
                    st.error("两次输入的密码不一致" if is_zh else "Passwords do not match")
                else:
                    try:
                        _store_auth(
                            auth_request(
                                "POST",
                                "/api/auth/register",
                                {
                                    "username": username,
                                    "email": email,
                                    "display_name": display_name,
                                    "password": password,
                                },
                            )
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def _render_account_sidebar() -> None:
    user = st.session_state.auth_user
    is_zh = st.session_state.get("language", "zh") == "zh"
    st.sidebar.divider()
    st.sidebar.caption("当前账号" if is_zh else "Signed in as")
    st.sidebar.write(f"**{user.get('display_name') or user.get('username')}**")
    st.sidebar.caption(user.get("email", ""))

    with st.sidebar.expander("修改密码" if is_zh else "Change password"):
        with st.form("change_password_form"):
            current_password = st.text_input("当前密码" if is_zh else "Current password", type="password")
            new_password = st.text_input(
                "新密码" if is_zh else "New password",
                type="password",
                help="至少 8 位，并同时包含字母和数字" if is_zh else "At least 8 characters with letters and numbers",
            )
            confirm_password = st.text_input("确认新密码" if is_zh else "Confirm new password", type="password")
            submitted = st.form_submit_button("确认修改" if is_zh else "Update password", use_container_width=True)
        if submitted:
            if new_password != confirm_password:
                st.error("两次输入的新密码不一致" if is_zh else "New passwords do not match")
            else:
                try:
                    result = auth_request(
                        "POST",
                        "/api/auth/change-password",
                        {"current_password": current_password, "new_password": new_password},
                    )
                    _store_auth(result)
                    st.success("密码已修改" if is_zh else "Password updated")
                except Exception as exc:
                    st.error(str(exc))

    if st.sidebar.button("退出登录" if is_zh else "Sign out", use_container_width=True):
        try:
            auth_request("POST", "/api/auth/logout")
        except Exception:
            pass
        _clear_auth()
        st.rerun()


def require_login() -> dict:
    st.session_state.setdefault("language", "zh")
    st.session_state.setdefault("auth_token", "")
    st.session_state.setdefault("auth_user", None)

    if st.session_state.auth_token:
        try:
            st.session_state.auth_user = auth_request("GET", "/api/auth/me")
        except Exception:
            _clear_auth()
            st.session_state.auth_token = ""
            st.session_state.auth_user = None

    if not st.session_state.auth_user:
        _render_login_page()
        st.stop()

    _render_account_sidebar()
    return st.session_state.auth_user
