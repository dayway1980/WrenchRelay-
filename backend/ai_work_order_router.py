"""Transcript-to-review work-order generation with explicit missing-field handling."""

import asyncio
import json
import os

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

from security import CurrentUser


router = APIRouter(prefix="/work-orders", tags=["ai work orders"])


class GenerateRequest(BaseModel):
    transcript: str = Field(min_length=2, max_length=12000)
    language: str = "en-US"


SYSTEM_PROMPT = """You are WrenchRelay AI, a maintenance documentation assistant. Analyze the technician's voice transcript and generate a structured work order. Identify the maintenance type (Electrical/Mechanical/Hydraulic/Pneumatic/Controls/Safety). Extract: Problem Description, Initial Condition, Troubleshooting Steps, Root Cause, Corrective Action, Parts Used, Safety Notes, Verification Steps. If information is missing, mark it as 'Not provided - follow up needed' and generate relevant follow-up questions. Never invent information. Always ask about LOTO for electrical work, pressure verification for hydraulic/pneumatic, and isolation for controls work. Return valid JSON with maintenance_type, problem, initial_condition, troubleshooting, root_cause, corrective_action, parts_used, safety_notes, verification, status, follow_up_questions."""


@router.post("/generate")
async def generate_work_order(payload: GenerateRequest, user: CurrentUser):
    response = await asyncio.to_thread(
        requests.post,
        f"{os.environ['OPENAI_BASE_URL'].rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        json={"model": "gpt-4o", "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": payload.transcript}], "response_format": {"type": "json_object"}, "temperature": 0.1},
        timeout=45,
    )
    response.raise_for_status()
    structured = json.loads(response.json()["choices"][0]["message"]["content"])
    return {"original_transcript": payload.transcript, "language": payload.language, "professional_version": structured, "follow_up_questions": structured.get("follow_up_questions", []), "requires_technician_review": True}
