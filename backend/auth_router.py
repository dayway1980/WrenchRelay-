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


class EmailRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=10, max_length=128)


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


class SeatRequest(BaseModel):
    seat_count: int = Field(ge=1, le=5000)
    plan: str = "Starter"


def public_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key not in {"_id", "password_hash"}}


@router.post("/register")
async def register(payload: RegisterRequest, response: Response):
    email = str(payload.email).lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account already exists for this email.")
    user = {
        "id": new_id(), "name": payload.name.strip(), "email": email, "password_hash": password_hash(payload.password),
        "relay_personality": "Professional", "preferred_units": "Imperial", "email_verified": True,
        "active": True, "created_at": now_iso(), "updated_at": now_iso(),
    }
    organization = {
        "id": new_id(), "name": payload.organization_name.strip(), "slug": payload.organization_name.lower().replace(" ", "-")[:48],
        "active": True, "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"],
        "integration_extensions": {"cmms": [], "sync_status": "not_configured"},
    }
    membership = {"id": new_id(), "organization_id": organization["id"], "user_id": user["id"], "role": "Owner", "active": True, "created_at": now_iso(), "updated_at": now_iso()}
    await db.users.insert_one(user)
    await db.organizations.insert_one(organization)
    await db.memberships.insert_one(membership)
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if stripe_key:
        try:
            stripe.api_key = stripe_key
            customer = stripe.Customer.create(email=user["email"], name=organization["name"], metadata={"organization_id": organization["id"]})
            trial_end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
            await db.organizations.update_one({"id": organization["id"]}, {"$set": {"stripe_customer_id": customer.id, "trial_end": trial_end, "subscription": {"plan": "trial", "trial_end": trial_end, "status": "trialing"}}})
        except stripe.StripeError:
            pass
    set_session(response, user)
    return {
        "user": public_user(user),
        "organization": {key: value for key, value in organization.items() if key != "_id"},
        "membership": {key: value for key, value in membership.items() if key != "_id"},
    }


@router.post("/login")
async def login(payload: LoginRequest, response: Response, request: Request):
    email = str(payload.email).lower()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier}, {"_id": 0})
    if attempt and attempt.get("locked_until"):
        try:
            locked_until = datetime.fromisoformat(attempt["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > datetime.now(timezone.utc):
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many sign-in attempts. Try again in 15 minutes.")
        except (ValueError, TypeError):
            await db.login_attempts.delete_one({"identifier": identifier})
    user = await db.users.find_one({"email": email})
    if not user or not password_matches(payload.password, user.get("password_hash")):
        failure_count = (attempt or {}).get("failure_count", 0) + 1
        updates = {"identifier": identifier, "failure_count": failure_count, "updated_at": now_iso()}
        if failure_count >= 5:
            updates["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": updates}, upsert=True)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    user.pop("_id", None)
    if not user.get("active", True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is inactive.")
    set_session(response, user)
    await db.login_attempts.delete_one({"identifier": identifier})
    return {"user": public_user(user)}


@router.post("/google/session")
async def exchange_google_session(payload: GoogleSessionRequest, response: Response):
    try:
        remote = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": payload.session_id}, timeout=20)
        remote.raise_for_status()
        identity = remote.json()
        email = identity["email"].lower()
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google session is invalid or expired.") from exc
    user = await db.users.find_one({"email": email})
    if not user:
        user = {"id": new_id(), "name": identity.get("name") or email.split("@")[0], "email": email, "password_hash": None, "relay_personality": "Professional", "preferred_units": "Imperial", "email_verified": True, "active": True, "created_at": now_iso(), "updated_at": now_iso(), "google_picture": identity.get("picture")}
        await db.users.insert_one(user)
    user.pop("_id", None)
    set_session(response, user)
    return {"user": public_user(user), "new_user": not bool(await db.memberships.find_one({"user_id": user["id"], "active": True}))}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite="none", secure=True)
    response.delete_cookie("wr_refresh", path="/", samesite="none", secure=True)
    return {"ok": True}


@router.get("/me")
async def me(user: CurrentUser):
    memberships = await db.memberships.find({"user_id": user["id"], "active": True}, {"_id": 0}).to_list(20)
    organizations = []
    for membership in memberships:
        organization = await db.organizations.find_one({"id": membership["organization_id"], "active": True}, {"_id": 0})
        if organization:
            organizations.append({**organization, "role": membership["role"]})
    return {"user": user, "organizations": organizations}


@router.patch("/profile")
async def update_profile(payload: ProfileRequest, user: CurrentUser):
    if payload.preferred_product not in {None, "industrial", "automotive"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose industrial or automotive.")
    if payload.preferred_language not in {None, "en-US", "es-MX"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose English or Español.")
    updates = {**payload.model_dump(exclude_unset=True), "updated_at": now_iso()}
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {**user, **updates}


@router.post("/organizations/{organization_id}/invites")
async def invite_member(organization_id: str, payload: InviteRequest, user: CurrentUser):
    await require_organization(user, organization_id, "members:read")
    allowed_roles = {"Admin", "Supervisor", "Technician", "Administrator", "Maintenance Manager", "Planner", "Senior Technician", "Storeroom", "Read Only"}
    if payload.role not in allowed_roles:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That role is not available.")
    invite = {"id": new_id(), "token": secrets.token_urlsafe(24), "organization_id": organization_id, "email": str(payload.email).lower(), "role": payload.role, "status": "pending", "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(), "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.invites.update_one({"organization_id": organization_id, "email": invite["email"], "status": "pending"}, {"$set": invite}, upsert=True)
    return {"invite": {key: value for key, value in invite.items() if key != "token"}, "delivery": "Email delivery is ready to configure; share the generated invitation from the administration view."}


@router.get("/organizations/{organization_id}/seats")
async def get_seats(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "members:read")
    organization = await db.organizations.find_one({"id": organization_id}, {"_id": 0})
    active_members = await db.memberships.count_documents({"organization_id": organization_id, "active": True})
    subscription = organization.get("subscription", {"plan": "Starter", "seat_count": 1, "billing_status": "Test mode"})
    return {"active_members": active_members, **subscription}


@router.put("/organizations/{organization_id}/seats")
async def update_seats(organization_id: str, payload: SeatRequest, user: CurrentUser):
    await require_organization(user, organization_id, "members:read")
    subscription = {"plan": payload.plan, "seat_count": payload.seat_count, "billing_status": "Test mode", "updated_at": now_iso()}
    await db.organizations.update_one({"id": organization_id}, {"$set": {"subscription": subscription, "updated_at": now_iso()}})
    return subscription


@router.post("/forgot-password")
async def forgot_password(payload: EmailRequest):
    user = await db.users.find_one({"email": str(payload.email).lower()}, {"_id": 0})
    reset_link = None
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"token": token, "user_id": user["id"], "expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "used": False})
        reset_link = f"{os.environ['FRONTEND_URL']}/reset-password?token={token}"
    return {"message": "If that account exists, reset instructions are ready for your configured email service.", "development_reset_link": reset_link if os.environ.get("EMAIL_PROVIDER", "none") == "none" else None}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    record = await db.password_reset_tokens.find_one({"token": payload.token, "used": False})
    if not record:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or expired.")
    expires_at = record["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or expired.")
    await db.users.update_one({"id": record["user_id"]}, {"$set": {"password_hash": password_hash(payload.password), "updated_at": now_iso()}})
    await db.password_reset_tokens.update_one({"token": payload.token}, {"$set": {"used": True}})
    return {"ok": True, "message": "Password updated. You can now sign in."}
