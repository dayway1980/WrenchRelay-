"""Identity, organization membership, invitations, and profile endpoints."""

import os
import secrets
from datetime import datetime, timedelta, timezone

import stripe
import requests
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from db import db, now_iso
from security import ACCESS_COOKIE, CurrentUser, new_id, password_hash, password_matches, require_organization, set_session

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    organization_name: str = Field(min_length=2, max_length=120)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleSessionRequest(BaseModel):
    session_id: str

class InviteRequest(BaseModel):
    email: EmailStr
    role: str

class ProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    relay_personality: str = "Straight Shooter"
    preferred_units: str = "Imperial"
    preferred_product: str | None = None
    preferred_language: str | None = None

def public_user(user):
    return {k: v for k, v in user.items() if k not in {'_id', 'password_hash'}}

@router.post("/register")
async def register(payload: RegisterRequest, response: Response):
    email = str(payload.email).lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Account exists.")
    user = {"id": new_id(), "name": payload.name.strip(), "email": email, "password_hash": password_hash(payload.password), "relay_personality": "Professional", "preferred_units": "Imperial", "email_verified": True, "active": True, "created_at": now_iso(), "updated_at": now_iso()}
    org = {"id": new_id(), "name": payload.organization_name.strip(), "slug": payload.organization_name.lower().replace(' ', '-')[:48], "active": True, "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"], "integration_extensions": {"cmms": [], "sync_status": "not_configured"}}
    mem = {"id": new_id(), "organization_id": org["id"], "user_id": user["id"], "role": "Owner", "active": True, "created_at": now_iso(), "updated_at": now_iso()}
    await db.users.insert_one(user)
    await db.organizations.insert_one(org)
    await db.memberships.insert_one(mem)
    set_session(response, user)
    return {"user": public_user(user), "organization": {k: v for k, v in org.items() if k != '_id'}, "membership": {k: v for k, v in mem.items() if k != '_id'}}

@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    email = str(payload.email).lower()
    user = await db.users.find_one({"email": email})
    if not user or not password_matches(payload.password, user.get("password_hash")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    user.pop("_id", None)
    set_session(response, user)
    return {"user": public_user(user)}

@router.post("/google/session")
async def exchange_google_session(payload: GoogleSessionRequest, response: Response):
    try:
        remote = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": payload.session_id}, timeout=20)
        remote.raise_for_status()
        identity = remote.json()
        email = identity["email"].lower()
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google session invalid.") from exc
    user = await db.users.find_one({"email": email})
    if not user:
        user = {"id": new_id(), "name": identity.get("name") or email.split("@")[0], "email": email, "password_hash": None, "relay_personality": "Professional", "preferred_units": "Imperial", "email_verified": True, "active": True, "created_at": now_iso(), "updated_at": now_iso()}
        await db.users.insert_one(user)
    user.pop("_id", None)
    set_session(response, user)
    return {"user": public_user(user), "new_user": not bool(await db.memberships.find_one({"user_id": user["id"], "active": True}))}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite="none", secure=True)
    return {"ok": True}

@router.get("/me")
async def me(user: CurrentUser):
    memberships = await db.memberships.find({"user_id": user["id"], "active": True}, {"_id": 0}).to_list(20)
    orgs = []
    for m in memberships:
        org = await db.organizations.find_one({"id": m["organization_id"], "active": True}, {"_id": 0})
        if org:
            orgs.append({**org, "role": m["role"]})
    return {"user": user, "organizations": orgs}

@router.patch("/profile")
async def update_profile(payload: ProfileRequest, user: CurrentUser):
    updates = {**payload.model_dump(exclude_unset=True), "updated_at": now_iso()}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {**user, **updates}

@router.post("/organizations/{organization_id}/invites")
async def invite_member(organization_id: str, payload: InviteRequest, user: CurrentUser):
    await require_organization(user, organization_id, "members:read")
    invite = {"id": new_id(), "token": secrets.token_urlsafe(24), "organization_id": organization_id, "email": str(payload.email).lower(), "role": payload.role, "status": "pending", "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(), "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.invites.update_one({"organization_id": organization_id, "email": invite["email"], "status": "pending"}, {"$set": invite}, upsert=True)
    return {"invite": {k: v for k, v in invite.items() if k != 'token'}}
