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


def safe_reply(command, mode, personality, action):
    prefix = {"Training": "Step by step: ", "Intermediate": "Here is the practical read: ", "Expert": "Result: "}[mode]
    tone = {"Laid Back": " Keep it steady.", "Funny": " One less clipboard adventure.", "Professional": "", "Hardcore": " Verify before you sign it off."}[personality]
    if action:
        return f"{prefix}{action['message']}{tone}"
    return f"AI assistant temporarily unavailable, please try again shortly. {prefix}I recorded your request.{tone}"


async def command_action(organization_id, user, text):
    open_match = re.search(r"(?:open|create) (?:a )?work order(?: for)? (.+)", text, re.IGNORECASE)
    if open_match:
        await require_organization(user, organization_id, "work_orders:write")
        title = open_match.group(1).strip()
        work_order = {"id": new_id(), "organization_id": organization_id, "work_order_number": f"VR-{datetime.now(timezone.utc).strftime('%H%M%S')}", "asset_id": None, "title": title, "description": f"Voice-created request: {text}", "priority": "Medium", "status": "New", "maintenance_type": "Corrective", "assigned_to": user["id"], "planned_parts": [], "planned_tasks": [], "readiness": "Awaiting Review", "readiness_reasons": ["Voice-created work order needs review."], "active": True, "archived": False, "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"], "updated_by": user["id"]}
        await db.work_orders.insert_one(work_order)
        return {"type": "created_work_order", "work_order_id": work_order["id"], "message": f"Opened work order {work_order['work_order_number']} for {title}."}
    return None


def proxy_reply(text, mode, personality, action):
    system = f"You are WrenchRelay by IdeasApplied, an industrial maintenance voice assistant. {MODE_INSTRUCTIONS[mode]} {PERSONALITY_INSTRUCTIONS[personality]} Never invent measurements or safety instructions."
    payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": system}, {"role": "user", "content": f"Technician said: {text}\nSystem action: {action or 'none'}"}], "temperature": 0.3, "max_tokens": 240}
    try:
        response = requests.post(f"{os.environ['OPENAI_BASE_URL'].rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("OpenAI command proxy unavailable: %s", exc)
        return safe_reply(text, mode, personality, action)


@router.post("/command")
async def process_command(organization_id: str, payload: AssistantCommand, user: CurrentUser):
    await require_organization(user, organization_id, "assistant:use")
    action = await command_action(organization_id, user, payload.text)
    reply = await asyncio.to_thread(proxy_reply, payload.text, payload.mode, payload.personality, action)
    record = {"id": new_id(), "organization_id": organization_id, "user_id": user["id"], "mode": payload.mode, "personality": payload.personality, "input": payload.text, "reply": reply, "action": action, "created_at": now_iso()}
    await db.ai_interactions.insert_one(record)
    return {key: value for key, value in record.items() if key != "_id"}
