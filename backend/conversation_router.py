"""Persistent, maintenance-first conversational work-order agent."""

import asyncio
import logging
import os
import re

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import db, now_iso
from security import CurrentUser, new_id, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


class ConversationInput(BaseModel):
    text: str = Field(min_length=2, max_length=4000)
    session_id: str | None = None
    mode: str = "Training"
    personality: str = "Professional"
    language: str = "English"


def system_prompt(mode: str, personality: str, context: list[dict]) -> str:
    depth = {"Training": "Explain each documentation field plainly and ask one short follow-up at a time.", "Intermediate": "Use practical context and ask only missing questions.", "Expert": "Be concise. Ask only the essential missing field."}.get(mode, "Ask concise follow-up questions.")
    tone = personality.strip() or "professional"
    return f"You are WrenchRelay, a direct {tone} industrial maintenance voice agent. {depth} Actively close documentation gaps one field at a time. Required fields are: problem/complaint, root cause, corrective action, parts used, LOTO yes/no, verification test, machine status after repair, and estimated downtime. After each technician response, ask one short, direct question for the next missing required field. Probe vague statements: ask what specifically failed, what exactly was repaired, or what verification was run. Attempt each required field twice; after two unanswered attempts, label it 'Not provided by technician' and move on. Never invent measurements, parts, technical procedures, safety authorization, CMMS confirmations, or any unspoken fact. Keep observed, suspected, verified, and unknown information distinct. Preserve technical terms such as PLC, HMI, VFD, RPM, and PSI in their original form."


async def local_action(organization_id: str, user: dict, text: str) -> dict | None:
    lower = text.lower()
    if "what work orders do i have" in lower:
        jobs = await db.work_orders.find({"organization_id": organization_id, "status": {"$in": ["New", "Assigned", "In Progress", "Waiting for Parts"]}}, {"_id": 0, "work_order_number": 1, "title": 1, "status": 1}).to_list(10)
        return {"type": "open_work_orders", "open_work_orders": jobs}
    select_match = re.search(r"(?:work on|start|open)\s+([a-z0-9]+(?:-[a-z0-9]+)+)", lower)
    if select_match:
        work_order = await db.work_orders.find_one({"organization_id": organization_id, "work_order_number": select_match.group(1).upper()}, {"_id": 0})
        if work_order:
            return {"type": "selected_work_order", "active_work_order": work_order}
    if re.search(r"\b(?:is|went) down\b", lower) or "create work order" in lower:
        title = text.strip()
        record = {"id": new_id(), "organization_id": organization_id, "work_order_number": f"VR-{new_id()[:6].upper()}", "title": title, "description": f"Conversational report: {text}", "priority": "High" if "down" in lower else "Medium", "status": "New", "maintenance_type": "Corrective", "active": True, "archived": False, "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"], "updated_by": user["id"], "planned_parts": [], "planned_tasks": [], "readiness": "Awaiting Review", "readiness_reasons": ["Conversation requires field confirmation."]}
        await db.work_orders.insert_one(record)
        return {"type": "created_work_order", "work_order_number": record["work_order_number"], "active_work_order": {key: value for key, value in record.items() if key != "_id"}}
    match = re.search(r"done with\s+([a-z0-9]+(?:-[a-z0-9]+)+).*(?:replaced|used) (.+)", lower)
    if match:
        result = await db.work_orders.update_one({"organization_id": organization_id, "work_order_number": match.group(1).upper()}, {"$set": {"status": "Completed", "completed_at": now_iso(), "updated_at": now_iso()}})
        if result.matched_count:
            return {"type": "completed_work_order", "work_order_number": match.group(1).upper(), "parts_noted": match.group(2)}
    return None


@router.post("/message")
async def message(organization_id: str, payload: ConversationInput, user: CurrentUser):
    await require_organization(user, organization_id, "assistant:use")
    session_id = payload.session_id or new_id()
    previous = await db.conversation_messages.find({"organization_id": organization_id, "session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(30)
    action = await local_action(organization_id, user, payload.text)
    active = (action or {}).get("active_work_order")
    progress = {"completed": [], "missing": ["Problem / Complaint", "Root Cause", "Corrective Action", "Parts Used", "LOTO performed", "Verification / Test", "Machine status after repair", "Estimated downtime"]}
    if active:
        existing = active.get("conversation_progress", {})
        progress = {"completed": existing.get("completed", []), "missing": existing.get("missing", progress["missing"])}
        if action["type"] == "created_work_order":
            await db.work_orders.update_one({"id": active["id"]}, {"$set": {"conversation_progress": progress}})
    messages = [{"role": item["role"], "content": item["content"]} for item in previous]
    if action and action["type"] == "open_work_orders":
        listed = "; ".join(f"{job['work_order_number']}: {job['title']}" for job in action["open_work_orders"])
        messages.append({"role": "system", "content": f"The technician's open work orders are: {listed}. Read them out clearly, then ask which one to work on."})
    messages.append({"role": "user", "content": payload.text})
    try:
        response = await asyncio.to_thread(requests.post, f"{os.environ['OPENAI_BASE_URL'].rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, json={"model": "gpt-4o", "messages": [{"role": "system", "content": system_prompt(payload.mode, payload.personality, previous)}] + messages, "temperature": 0.35, "max_tokens": 260}, timeout=30)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()
        live = True
    except Exception as exc:
        logger.warning("Conversation model request unavailable: %s", exc)
        reply = "AI assistant temporarily unavailable, please try again shortly. What is the asset ID and current production impact?"
        live = False
    now = now_iso()
    await db.conversation_messages.insert_many([{"id": new_id(), "organization_id": organization_id, "session_id": session_id, "role": "user", "content": payload.text, "created_at": now}, {"id": new_id(), "organization_id": organization_id, "session_id": session_id, "role": "assistant", "content": reply, "created_at": now}])
    return {"session_id": session_id, "reply": reply, "live": live, "action": action, "progress": progress}
