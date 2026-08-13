"""Encrypted, organization-scoped generic CMMS configuration and previews."""

import os
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import db, now_iso
from security import CurrentUser, new_id, require_organization

router = APIRouter(prefix="/organizations/{organization_id}/cmms", tags=["cmms"])

TEMPLATES = {
    "Fiix": {"base_url": "https://YOUR-SITE.macmms.com/api/", "field_mappings": {"work_order_number": "id", "title": "description", "status": "status"}, "operations": {"create_work_order": "addWorkOrder", "update_status": "updateWorkOrder", "close_job": "closeWorkOrder", "fetch_asset_history": "findAsset"}},
    "UpKeep": {"base_url": "https://api.onupkeep.com/api/v2", "field_mappings": {"work_order_number": "id", "title": "title", "status": "status"}, "operations": {"create_work_order": "/work-orders", "update_status": "/work-orders/{id}", "close_job": "/work-orders/{id}", "fetch_asset_history": "/assets/{id}"}},
    "Limble": {"base_url": "https://api.limblecmms.com:443/v2", "field_mappings": {"work_order_number": "id", "title": "taskName", "status": "status"}, "operations": {"create_work_order": "/tasks", "update_status": "/tasks/{id}", "close_job": "/tasks/{id}", "fetch_asset_history": "/assets/{id}"}},
    "eMaint": {"base_url": "", "field_mappings": {"work_order_number": "id", "title": "description", "status": "status"}, "operations": {"create_work_order": "/work-orders", "update_status": "/work-orders/{id}", "close_job": "/work-orders/{id}", "fetch_asset_history": "/assets/{id}"}},
    "Generic REST": {"base_url": "", "field_mappings": {"work_order_number": "id", "title": "title", "status": "status"}, "operations": {"create_work_order": "/work-orders", "update_status": "/work-orders/{id}", "close_job": "/work-orders/{id}", "fetch_asset_history": "/assets/{id}"}},
}

class CmmsConfigInput(BaseModel):
    provider: str
    base_url: str = Field(min_length=0, max_length=500)
    api_key: str = Field(min_length=0, max_length=1000)
    field_mappings: dict[str, str]

def cipher():
    return Fernet(os.environ["CMMS_ENCRYPTION_KEY"].encode())

def public_config(config):
    return {"provider": config["provider"], "base_url": config["base_url"], "field_mappings": config["field_mappings"], "api_key_configured": bool(config.get("api_key_encrypted")), "tested_at": config.get("tested_at"), "enabled": config.get("enabled", False), "operations": TEMPLATES[config["provider"]]["operations"]}

@router.get("/templates")
async def templates(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "cmms:manage")
    return TEMPLATES

@router.get("/config")
async def get_config(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "cmms:manage")
    config = await db.cmms_configs.find_one({"organization_id": organization_id}, {"_id": 0})
    return public_config(config) if config else None

@router.put("/config")
async def save_config(organization_id: str, payload: CmmsConfigInput, user: CurrentUser):
    await require_organization(user, organization_id, "cmms:manage")
    if payload.provider not in TEMPLATES:
        raise HTTPException(422, "Choose a supported CMMS template.")
    config = {"id": new_id(), "organization_id": organization_id, "provider": payload.provider, "base_url": payload.base_url.rstrip("/"), "api_key_encrypted": cipher().encrypt(payload.api_key.encode()).decode() if payload.api_key else "", "field_mappings": payload.field_mappings, "tested_at": None, "enabled": False, "created_by": user["id"], "updated_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.cmms_configs.update_one({"organization_id": organization_id}, {"$set": config}, upsert=True)
    return public_config(config)
