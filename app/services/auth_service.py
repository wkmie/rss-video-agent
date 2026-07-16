from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import User, UserSession


PASSWORD_ITERATIONS = 600_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符")
    if len(password) > 128:
        raise ValueError("密码不能超过 128 个字符")
    if not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise ValueError("密码必须同时包含字母和数字")


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name or user.username,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def create_user(db: Session, username: str, email: str, password: str, display_name: str = "") -> User:
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()
    normalized_display_name = display_name.strip()

    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise ValueError("用户名需为 3-32 位字母、数字或下划线")
    if not EMAIL_PATTERN.fullmatch(normalized_email) or len(normalized_email) > 254:
        raise ValueError("请输入有效的邮箱地址")
    if len(normalized_display_name) > 80:
        raise ValueError("显示名称不能超过 80 个字符")
    validate_password(password)

    existing = db.scalar(
        select(User).where(or_(func.lower(User.username) == normalized_username, func.lower(User.email) == normalized_email))
    )
    if existing:
        if existing.username.lower() == normalized_username:
            raise ValueError("该用户名已被注册")
        raise ValueError("该邮箱已被注册")

    user = User(
        username=normalized_username,
        email=normalized_email,
        display_name=normalized_display_name or None,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("用户名或邮箱已被注册") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    normalized = identifier.strip().lower()
    user = db.scalar(
        select(User).where(or_(func.lower(User.username) == normalized, func.lower(User.email) == normalized))
    )
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise ValueError("用户名、邮箱或密码不正确")
    return user


def create_session(db: Session, user: User) -> str:
    db.execute(delete(UserSession).where(UserSession.expires_at <= _utcnow()))
    raw_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=_utcnow() + timedelta(days=max(settings.auth_session_days, 1)),
    )
    db.add(session)
    db.commit()
    return raw_token


def authenticate_token(db: Session, raw_token: str) -> tuple[User, UserSession]:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not session or _as_utc(session.expires_at) <= _utcnow():
        if session:
            db.delete(session)
            db.commit()
        raise ValueError("登录已过期，请重新登录")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise ValueError("账号不可用")
    session.last_used_at = _utcnow()
    db.commit()
    return user, session


def revoke_session(db: Session, raw_token: str) -> None:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> str:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("当前密码不正确")
    if hmac.compare_digest(current_password, new_password):
        raise ValueError("新密码不能与当前密码相同")
    user.password_hash = hash_password(new_password)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    db.refresh(user)
    return create_session(db, user)
