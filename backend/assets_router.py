"""Authenticated organization-scoped asset list and history endpoints."""

from fastapi import APIRouter, HTTPException

from db import db
from security import CurrentUser, require_organization


router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
async def list_assets(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "assets:read")
    assets = await db.assets.find({"organization_id": organization_id, "archived": {"$ne": True}}, {"_id": 0}).sort("asset_name", 1).to_list(1000)
    return {"assets": assets}


@router.get("/{asset_id}")
async def get_asset(asset_id: str, organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "assets:read")
    asset = await db.assets.find_one({"id": asset_id, "organization_id": organization_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    work_orders = await db.work_orders.find({"asset_id": asset_id, "organization_id": organization_id, "archived": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"asset": asset, "work_orders": work_orders}