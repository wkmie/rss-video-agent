from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_dependencies import require_auth_context, require_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.auth_service import (
    authenticate_user,
    change_password,
    create_session,
    create_user,
    revoke_session,
    user_payload,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


def auth_response(db: Session, user: User) -> dict:
    return {"access_token": create_session(db, user), "token_type": "bearer", "user": user_payload(user)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user = create_user(db, payload.username, payload.email, payload.password, payload.display_name)
        return auth_response(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return auth_response(db, authenticate_user(db, payload.identifier, payload.password))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me")
def me(user: User = Depends(require_current_user)) -> dict:
    return user_payload(user)


@router.post("/logout")
def logout(
    context: tuple[User, str] = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _, token = context
    revoke_session(db, token)
    return {"ok": True}


@router.post("/change-password")
def update_password(
    payload: ChangePasswordRequest,
    context: tuple[User, str] = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    user, _ = context
    try:
        token = change_password(db, user, payload.current_password, payload.new_password)
        return {"access_token": token, "token_type": "bearer", "user": user_payload(user)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
