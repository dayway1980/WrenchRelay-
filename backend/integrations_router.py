"""Customer-managed Fiix credential test and encrypted storage."""

import asyncio

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from cmms_router import cipher
from db import db, now_iso
from security import CurrentUser, require_organization


router = APIRouter(prefix="/integrations/fiix", tags=["fiix"])


class FiixInput(BaseModel):
    organization_id: str
    api_key: str
    api_secret: str = ""
    instance_url: str


async def verify(instance_url: str, api_key: str) -> tuple[bool, str]:
    if not instance_url.startswith("https://"):
        return False, "Fiix instance URL must use HTTPS."
    try:
        response = await asyncio.to_thread(requests.get, f"{instance_url.rstrip('/')}/api/v2/workorders", headers={"Authorization": f"Bearer {api_key}"}, params={"limit": 1}, timeout=10)
        return response.status_code == 200, "Successfully connected to Fiix" if response.status_code == 200 else f"Fiix returned {response.status_code}"
    except requests.RequestException:
        return False, "Fiix could not be reached. Check the instance URL and network connection."


@router.post("/test")
async def test(payload: FiixInput, user: CurrentUser):
    await require_organization(user, payload.organization_id, "cmms:manage")
    ok, message = await verify(payload.instance_url, payload.api_key)
    return {"status": "connected" if ok else "error", "message": message}


@router.post("/save")
async def save(payload: FiixInput, user: CurrentUser):
    await require_organization(user, payload.organization_id, "cmms:manage")
    if not payload.instance_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="Fiix instance URL must use HTTPS.")
    encrypted = cipher().encrypt(payload.api_key.encode()).decode()
    await db.organizations.update_one({"id": payload.organization_id}, {"$set": {"fiix": {"instance_url": payload.instance_url.rstrip("/"), "api_key_encrypted": encrypted, "api_secret_encrypted": cipher().encrypt(payload.api_secret.encode()).decode(), "status": "Not Connected", "updated_at": now_iso()}}})
    return {"ok": True, "status": "Not Connected"}


@router.get("/status")
async def status(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "cmms:manage")
    org = await db.organizations.find_one({"id": organization_id}, {"_id": 0, "fiix": 1})
    fiix = (org or {}).get("fiix", {})
    return {"status": fiix.get("status", "Not Connected"), "instance_url": fiix.get("instance_url"), "configured": bool(fiix.get("api_key_encrypted"))}
