"""Authentication, tenant validation, and permission helpers."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status

from db import db


JWT_ALGORITHM = "HS256"
ACCESS_COOKIE = "wr_access"
REFRESH_COOKIE = "wr_refresh"

ROLE_PERMISSIONS = {
    "Owner": {"*"},
    "Admin": {"*"},
    "Administrator": {"*"},
    "Supervisor": {"assistant:use", "assets:read", "work_orders:read", "closeouts:approve", "closeouts:read"},
    "Technician": {"assistant:use", "assets:read", "work_orders:write", "closeouts:write"},
    "Maintenance Manager": {"assets:write", "work_orders:write", "closeouts:approve", "members:read"},
    "Planner": {"assets:read", "work_orders:write", "kits:write", "closeouts:read"},
    "Senior Technician": {"assets:read", "work_orders:write", "closeouts:approve", "knowledge:write"},
    "Storeroom": {"assets:read", "work_orders:read", "kits:write"},
    "Read Only": {"assets:read", "work_orders:read", "closeouts:read"},
}


def password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def password_matches(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _token(payload: dict, duration: timedelta) -> str:
    body = {**payload, "exp": datetime.now(timezone.utc) + duration}
    return jwt.encode(body, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def access_token(user_id: str, email: str) -> str:
    return _token({"sub": user_id, "email": email, "type": "access"}, timedelta(minutes=15))


def refresh_token(user_id: str) -> str:
    return _token({"sub": user_id, "type": "refresh"}, timedelta(days=7))


def set_session(response, user: dict) -> None:
    response.set_cookie(ACCESS_COOKIE, access_token(user["id"], user["email"]), httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(REFRESH_COOKIE, refresh_token(user["id"]), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization[7:]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in is required.")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise ValueError("Wrong token type")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.") from exc
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user or not user.get("active", True):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account unavailable.")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def organization_membership(user_id: str, organization_id: str) -> dict:
    membership = await db.memberships.find_one(
        {"user_id": user_id, "organization_id": organization_id, "active": True}, {"_id": 0}
    )
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not belong to this organization.")
    return membership


async def require_organization(user: dict, organization_id: str, permission: str = "work_orders:read") -> dict:
    membership = await organization_membership(user["id"], organization_id)
    permissions = ROLE_PERMISSIONS.get(membership["role"], set())
    if "*" not in permissions and permission not in permissions:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not permit that action.")
    return membership


def new_id() -> str:
    return str(uuid.uuid4())
