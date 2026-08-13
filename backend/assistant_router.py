"""AI voice/text command layer with organization-scoped command actions."""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import db, now_iso
from security import CurrentUser, new_id, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

MODE_INSTRUCTIONS = {
    "Training": "Explain the workflow step by step, define maintenance terms plainly, and confirm each assumption.",
    "Intermediate": "Give practical context with concise reasoning and one next best action.",
    "Expert": "Be terse, precise, and fast. Use accepted maintenance terminology without basic explanations.",
}

PERSONALITY_INSTRUCTIONS = {
    "Laid Back": "Use calm, practical language.",
    "Funny": "Use light, appropriate shop humor only when it does not reduce clarity or seriousness.",
    "Professional": "Use formal, neutral language.",
    "Hardcore": "Be direct and disciplined. Challenge unclear assumptions without being hostile.",
}


class AssistantCommand(BaseModel):
    text: str = Field(min_length=2, max_length=4000)
    mode: str = "Intermediate"
    personality: str = "Professional"


def safe_reply(command: str, mode: str, personality: str, action: dict | None) -> str:
    prefix = {
        "Training": "Step by step: ",
        "Intermediate": "Here is the practical read: ",
        "Expert": "Result: ",
    }[mode]
    tone = {"Laid Back": " Keep it steady.", "Funny": " One less clipboard adventure.", "Professional": "", "Hardcore": " Verify before you sign it off."}[personality]
    if action:
        return f"{prefix}{action['message']}{tone}"
    return f"AI assistant temporarily unavailable, please try again shortly. {prefix}I recorded your request. I need an approved work-order or asset reference before making an operational change.{tone}"


async def command_action(organization_id: str, user: dict, text: str) -> dict | None:
    normalized = text.strip().lower()
    open_match = re.search(r"(?:open|create) (?:a )?work order(?: for)? (.+)", text, re.IGNORECASE)
    if open_match:
        await require_organization(user, organization_id, "work_orders:write")
        title = open_match.group(1).strip()
        work_order = {"id": new_id(), "organization_id": organization_id, "work_order_number": f"VR-{datetime.now(timezone.utc).strftime('%H%M%S')}", "asset_id": None, "title": title, "description": f"Voice-created request: {text}", "priority": "Medium", "status": "New", "maintenance_type": "Corrective", "assigned_to": user["id"], "planned_parts": [], "planned_tasks": [], "readiness": "Awaiting Review", "readiness_reasons": ["Voice-created work order needs review."], "active": True, "archived": False, "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"], "updated_by": user["id"]}
        await db.work_orders.insert_one(work_order)
        return {"type": "created_work_order", "work_order_id": work_order["id"], "message": f"Opened work order {work_order['work_order_number']} for {title}."}
    status_match = re.search(r"mark (?:wo[-\s]?)?([a-z0-9-]+) (?:as )?([a-z ]+)", normalized)
    if status_match:
        await require_organization(user, organization_id, "work_orders:write")
        number = status_match.group(1).upper()
        requested = status_match.group(2).strip()
        status_map = {"in progress": "In Progress", "assigned": "Assigned", "completed": "Completed", "closed": "Closed", "waiting for parts": "Waiting for Parts"}
        if requested in status_map:
            result = await db.work_orders.update_one({"organization_id": organization_id, "work_order_number": number}, {"$set": {"status": status_map[requested], "updated_at": now_iso(), "updated_by": user["id"]}})
            if result.matched_count:
                return {"type": "updated_status", "message": f"Marked {number} as {status_map[requested]}."}
    close_match = re.search(r"close (?:wo[-\s]?)?([a-z0-9-]+)(?:,|\s)(.+)", normalized)
    if close_match:
        await require_organization(user, organization_id, "work_orders:write")
        number, summary = close_match.group(1).upper(), close_match.group(2).strip()
        work_order = await db.work_orders.find_one({"organization_id": organization_id, "work_order_number": number}, {"_id": 0})
        if work_order:
            await db.work_orders.update_one({"id": work_order["id"]}, {"$set": {"status": "Completed", "completed_at": now_iso(), "updated_at": now_iso(), "updated_by": user["id"]}})
            await db.closeouts.update_one({"organization_id": organization_id, "work_order_id": work_order["id"]}, {"$set": {"id": new_id(), "organization_id": organization_id, "work_order_id": work_order["id"], "technician_summary": summary.capitalize(), "status": "Submitted", "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"], "updated_by": user["id"]}}, upsert=True)
            return {"type": "closed_work_order", "message": f"Closed {number} and submitted the voice closeout for review."}
    return None


def proxy_reply(text: str, mode: str, personality: str, action: dict | None) -> str:
    system = f"You are WrenchRelay by IdeasApplied, an industrial maintenance voice assistant. {MODE_INSTRUCTIONS[mode]} {PERSONALITY_INSTRUCTIONS[personality]} Never invent measurements, diagnostic results, safety instructions, technical procedures, work authorization, or CMMS confirmations. Do not tell a technician to perform lockout, disassembly, inspection, or any action that requires site-approved procedures. You may organize facts, identify unknowns, and state when human review is required."
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": system}, {"role": "user", "content": f"Technician said: {text}\nSystem action: {action or 'none'}"}], "temperature": 0.3, "max_tokens": 240}
    try:
        response = requests.post(f"{os.environ['OPENAI_BASE_URL'].rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
        logger.warning("OpenAI command proxy unavailable: %s", exc)
        return safe_reply(text, mode, personality, action)


@router.post("/command")
async def process_command(organization_id: str, payload: AssistantCommand, user: CurrentUser):
    await require_organization(user, organization_id, "assistant:use")
    if payload.mode not in MODE_INSTRUCTIONS or payload.personality not in PERSONALITY_INSTRUCTIONS:
        raise HTTPException(status_code=422, detail="Select a supported AI mode and personality.")
    action = await command_action(organization_id, user, payload.text)
    reply = await asyncio.to_thread(proxy_reply, payload.text, payload.mode, payload.personality, action)
    record = {"id": new_id(), "organization_id": organization_id, "user_id": user["id"], "mode": payload.mode, "personality": payload.personality, "input": payload.text, "reply": reply, "action": action, "created_at": now_iso()}
    await db.ai_interactions.insert_one(record)
    return {key: value for key, value in record.items() if key != "_id"}


@router.get("/asset-history/{asset_number}")
async def asset_history(organization_id: str, asset_number: str, user: CurrentUser):
    await require_organization(user, organization_id, "assistant:use")
    asset = await db.assets.find_one({"organization_id": organization_id, "asset_number": asset_number}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    jobs = await db.work_orders.find({"organization_id": organization_id, "asset_id": asset["id"]}, {"_id": 0, "work_order_number": 1, "title": 1, "status": 1, "updated_at": 1}).sort("updated_at", -1).to_list(20)
    return {"asset": asset, "work_orders": jobs}
