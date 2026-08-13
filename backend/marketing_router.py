"""Public lead capture for the WrenchRelay landing page."""

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from db import db, now_iso
from security import new_id


router = APIRouter(prefix="/public", tags=["marketing"])


class DemoRequestInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str = Field(min_length=2, max_length=160)


@router.post("/demo-requests")
async def demo_request(payload: DemoRequestInput):
    record = {"id": new_id(), "name": payload.name.strip(), "email": str(payload.email).lower(), "company": payload.company.strip(), "status": "New", "created_at": now_iso(), "updated_at": now_iso()}
    await db.demo_requests.update_one({"email": record["email"], "company": record["company"]}, {"$set": record}, upsert=True)
    return {"ok": True, "message": "Your demo request has been received."}