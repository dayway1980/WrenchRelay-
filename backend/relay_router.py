"""Grounded Relay assistant endpoints with safe deterministic fallbacks."""

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db import db, now_iso
from security import CurrentUser, new_id, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/relay", tags=["relay"])


class RelayRequest(BaseModel):
    work_order_id: str | None = None
    question: str = Field(min_length=2, max_length=4000)
    personality: str = "Straight Shooter"


def follow_up_questions(entries: list[dict]) -> list[str]:
    content = " ".join(entry.get("body", "").lower() for entry in entries)
    candidates = [
        ("machine stopped", "Is the machine stopped or still running?"),
        ("production", "Did production stop or continue?"),
        ("measure", "What did you measure, and what unit applies?"),
        ("inspect", "What did you inspect?"),
        ("verified", "How was operation verified afterward?"),
        ("part", "Which parts were used, returned, or unavailable?"),
    ]
    return [question for term, question in candidates if term not in content][:3]


def draft_from_entries(entries: list[dict]) -> dict:
    notes = [entry.get("body", "").strip() for entry in entries if entry.get("body", "").strip()]
    observed = " ".join(notes[:3]) or "No technician observations have been recorded."
    return {
        "technician_summary": observed[:560],
        "problem_reported": "Technician record pending confirmation.",
        "observations": observed,
        "corrective_action": "Not yet confirmed by the technician.",
        "verification": "Verification has not been recorded.",
        "cause_confidence": "Probable",
        "unresolved_conditions": "Review unanswered follow-up questions before approval.",
        "notice": "Relay organized the available record. Human review is required before approval.",
    }


@router.get("/work-orders/{work_order_id}/prepare")
async def prepare_job(organization_id: str, work_order_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:read")
    work_order = await db.work_orders.find_one({"id": work_order_id, "organization_id": organization_id}, {"_id": 0})
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found.")
    kit_items = []
    for part in work_order.get("planned_parts", []):
        kit_items.append({"name": part.get("name", "Planned part"), "suggested": part.get("quantity", 1), "approved": 0, "picked": 0, "used": 0, "returned": 0, "provenance": "Planned on current work order"})
    similar = await db.work_orders.find({"organization_id": organization_id, "id": {"$ne": work_order_id}, "status": {"$in": ["Completed", "Closed"]}}, {"_id": 0, "work_order_number": 1, "title": 1, "description": 1}).limit(3).to_list(3)
    matches = [{"work_order_number": item["work_order_number"], "title": item["title"], "reason": "Similar work title in this organization", "confidence": "Context only"} for item in similar if item["title"].lower()[:12] in work_order["title"].lower() or work_order["title"].lower()[:12] in item["title"].lower()]
    return {"job_readiness": {"state": "Ready with Exceptions" if not kit_items else "Awaiting Review", "reasons": ["Confirm documents, parts, and assignment before starting work."]}, "suggested_kit": kit_items, "similar_jobs": matches, "safety_notice": "Previous work provides context but does not establish the current cause."}


@router.get("/work-orders/{work_order_id}/draft")
async def closeout_draft(organization_id: str, work_order_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "closeouts:write")
    entries = await db.technician_entries.find({"organization_id": organization_id, "work_order_id": work_order_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return {"draft": draft_from_entries(entries), "follow_up_questions": follow_up_questions(entries)}


@router.post("/mentor")
async def mentor(organization_id: str, payload: RelayRequest, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:read")
    sources = await db.knowledge_sources.find({"organization_id": organization_id, "status": "Approved"}, {"_id": 0}).limit(4).to_list(4)
    await db.relay_messages.insert_one({"id": new_id(), "organization_id": organization_id, "user_id": user["id"], "question": payload.question, "personality": payload.personality, "created_at": now_iso()})
    if not sources:
        return {"answer": "I could not find an approved source for that answer.", "sources": [], "mode": "grounded"}
    excerpts = [source.get("summary", source.get("title", "Approved knowledge")) for source in sources]
    return {"answer": "Approved context is available below. Review the source before acting; Relay does not provide safety procedures or work authorization.", "sources": [{"title": source.get("title", "Approved knowledge"), "excerpt": excerpt, "status": "Approved"} for source, excerpt in zip(sources, excerpts)], "mode": "grounded"}


@router.post("/stream")
async def relay_stream(organization_id: str, payload: RelayRequest, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:read")

    async def event_stream() -> AsyncIterator[str]:
        fallback = "Relay is ready to organize technician observations. It will not create measurements, diagnoses, procedures, or safety authorization."
        try:
            import os
            import requests

            system_message = "You are Relay, a maintenance documentation assistant. Use only the user-provided text and approved sources. Do not invent measurements, technical procedures, diagnoses, safety instructions, or work authorization. Ask one concise unanswered documentation question or state that approved sources are unavailable."
            response = requests.post(
                f"{os.environ['OPENAI_BASE_URL'].rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
                json={"model": "gpt-4o", "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": payload.question}], "stream": True},
                stream=True,
                timeout=45,
            )
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                chunk = line[6:]
                if chunk == "[DONE]":
                    break
                event = json.loads(chunk)
                token = event.get("choices", [{}])[0].get("delta", {}).get("content")
                if token:
                    yield f"data: {json.dumps({'text': token})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'text': fallback, 'fallback': True})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
