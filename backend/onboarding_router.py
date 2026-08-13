"""Resumable customer onboarding progress for each organization."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import db, now_iso
from security import CurrentUser, new_id, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/onboarding", tags=["onboarding"])

STEPS = [
    ("organization", "Confirm organization details"),
    ("site", "Add your first site"),
    ("location", "Add your first location"),
    ("asset", "Add your first asset"),
    ("invite", "Invite a technician"),
    ("work_order", "Create or import a work order"),
    ("entry", "Record the first technician entry"),
    ("closeout", "Approve the first closeout"),
    ("export", "Export the first record"),
]


class ProgressInput(BaseModel):
    step_id: str
    completed: bool


async def progress_payload(organization_id: str) -> dict:
    progress = await db.onboarding_progress.find_one({"organization_id": organization_id}, {"_id": 0})
    completed_steps = set((progress or {}).get("completed_steps", []))
    return {"steps": [{"id": step_id, "label": label, "completed": step_id in completed_steps} for step_id, label in STEPS], "completed_count": len(completed_steps), "total_count": len(STEPS), "updated_at": (progress or {}).get("updated_at")}


@router.get("")
async def get_progress(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:read")
    return await progress_payload(organization_id)


@router.put("")
async def update_progress(organization_id: str, payload: ProgressInput, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:write")
    valid_steps = {step_id for step_id, _ in STEPS}
    if payload.step_id not in valid_steps:
        raise HTTPException(status_code=422, detail="Unknown onboarding step.")
    current = await db.onboarding_progress.find_one({"organization_id": organization_id}, {"_id": 0}) or {"id": new_id(), "organization_id": organization_id, "completed_steps": [], "created_at": now_iso(), "created_by": user["id"]}
    completed_steps = set(current["completed_steps"])
    if payload.completed:
        completed_steps.add(payload.step_id)
    else:
        completed_steps.discard(payload.step_id)
    current.update({"completed_steps": sorted(completed_steps), "updated_at": now_iso(), "updated_by": user["id"]})
    await db.onboarding_progress.update_one({"organization_id": organization_id}, {"$set": current}, upsert=True)
    return await progress_payload(organization_id)
