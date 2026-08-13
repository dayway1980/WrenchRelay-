"""Gemini 3.1 Pro Preview streaming chat for Relay conversations."""

import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db import db, now_iso
from security import CurrentUser, new_id, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/gemini", tags=["gemini"])


class GeminiChatInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=12000)


SYSTEM_PROMPT = """You are Relay, an industrial maintenance documentation assistant. Use only facts supplied by the technician or approved organization context. Never invent measurements, part numbers, root causes, safety actions, repairs, work authorization, or verification results. Ask concise follow-up questions only when materially needed. Clearly distinguish observed, suspected, verified, and unknown information."""


@router.post("/chat/stream")
async def stream_chat(organization_id: str, payload: GeminiChatInput, user: CurrentUser):
    await require_organization(user, organization_id, "assistant:use")

    async def events():
        from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage

        output = []
        await db.conversation_messages.insert_one({"id": new_id(), "organization_id": organization_id, "session_id": payload.session_id, "role": "user", "content": payload.message, "created_at": now_iso()})
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=payload.session_id, system_message=SYSTEM_PROMPT).with_model("gemini", "gemini-3.1-pro-preview")
        try:
            async for event in chat.stream_message(UserMessage(text=payload.message)):
                if isinstance(event, TextDelta):
                    output.append(event.content)
                    yield f"data: {event.content}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception:
            yield "data: AI temporarily unavailable. Your technician message is saved. Please try again shortly.\n\n"
        finally:
            if output:
                await db.conversation_messages.insert_one({"id": new_id(), "organization_id": organization_id, "session_id": payload.session_id, "role": "assistant", "content": "".join(output), "created_at": now_iso()})
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
