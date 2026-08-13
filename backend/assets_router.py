"""Assets router — CRUD for equipment / asset records.

Provides endpoints to list, create, update, and get individual assets
belonging to the authenticated user's workspace.
"""

from fastapi import APIRouter, Depends, HTTPException
from .db import get_db
from .security import get_current_user

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
async def list_assets(db=Depends(get_db), user=Depends(get_current_user)):
    result = db.table("assets").select("*").eq("workspace_id", user["workspace_id"]).execute()
    return result.data


@router.get("/{asset_id}")
async def get_asset(asset_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    result = db.table("assets").select("*").eq("id", asset_id).eq("workspace_id", user["workspace_id"]).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Asset not found")
    return result.data


@router.post("")
async def create_asset(payload: dict, db=Depends(get_db), user=Depends(get_current_user)):
    payload["workspace_id"] = user["workspace_id"]
    result = db.table("assets").insert(payload).execute()
    return result.data[0] if result.data else {}
