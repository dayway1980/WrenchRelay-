"""Opt-in Realtime voice credential bridge for WrenchRelay.

The permanent OpenAI key never leaves this authenticated backend.
Default OFF: a positive budget approval and an explicit rollout flag are required.
This bridge does NOT control equipment, update work orders, or execute tool calls.

IMPORTANT: daily token-issuance quotas and a browser timer are NOT provider-side
duration caps. Keep feature disabled until account-level API spending controls,
monitoring, and staging tests are verified.
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Literal

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

VOICE_MODEL = "gpt-realtime-2.1"
VOICE_PROVIDER_URL = "https://api.openai.com/v1/realtime/client_secrets"
MAX_SESSIONS_PER_USER_DAY = 2
SECRET_TTL_SECONDS = 60

# Production approval is TWO independent settings; both default to disabled.
def realtime_enabled() -> bool:
    return (
        os.getenv("WRENCHRELAY_REALTIME_ENABLED", "").strip().lower() == "true"
        and os.getenv("WRENCHRELAY_REALTIME_BUDGET_APPROVED", "").strip().lower() == "true"
        and bool(os.getenv("OPENAI_API_KEY"))
    )


class VoiceRequest(BaseModel):
    mode: Literal["industrial", "automotive"] = "industrial"
    language: Literal["English", "Spanish"] = "English"


def _allowed_origins() -> set[str]:
    defaults = {
        "https://wrenchrelay.com",
        "https://www.wrenchrelay.com",
        "https://app.wrenchrelay.com",
        "https://wrenchrelayllc.com",
        "https://www.wrenchrelayllc.com",
    }
    extras = {
        origin.strip().rstrip("/")
        for origin in os.getenv("WRENCHRELAY_REALTIME_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    }
    # Explicit allowed origins only; never reflect an arbitrary Origin.
    return defaults | extras


def validate_origin(origin: str | None) -> None:
    if not origin or origin.rstrip("/") not in _allowed_origins():
        raise HTTPException(status_code=403, detail="Voice request origin is not allowed.")


def _instructions(mode: str, language: str) -> str:
    scope = (
        "INDUSTRIAL: PLCs, controls, drives, mechanical equipment, hydraulics and plant maintenance."
        if mode == "industrial"
        else "AUTOMOTIVE: vehicle symptoms, diagnostic trouble codes, electrical, mechanical, and repair notes."
    )
    locale = "Speak Spanish naturally." if language == "Spanish" else "Speak English naturally."
    return (
        "You are WrenchRelay's conversational MAINTENANCE NOTE assistant. "
        + locale + " " + scope + " "
        "Ask ONE short question at a time to document a repair or troubleshooting event. "
        "Capture: reported problem, observations and measurements, actual tests, energy isolation "
        "and safety controls, actions and parts, and verification of the outcome. "
        "Say 'not documented' if the technician has not supplied the answer. "
        "Separate DIRECT OBSERVATIONS, POSSIBLE CAUSES and VERIFIED RESULTS. "
        "Never invent a measurement, part, test result, root cause, confirmed fix or approval. "
        "Do not give hazardous instructions or suggest bypassing LOTO, guarding, interlocks, "
        "electrical protections, vehicle safety systems, permits or OEM procedures. "
        "Do not claim authority to release equipment for service. Escalate safety concerns "
        "to qualified staff. You cannot touch CMMS, files, machinery, payments or accounts; "
        "no tools are available. Ask the technician to review the transcript independently "
        "before writing any official maintenance procedure. Keep each response concise."
    )


def _usage_key() -> str:
    return "realtime_sessions." + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _reserve_daily_token(db, email: str, key: str) -> bool:
    # Atomic per-account token cap even under concurrent browser tabs.
    before = db.users.find_one_and_update(
        {
            "email": email.lower(),
            "$or": [{key: {"$exists": False}}, {key: {"$lt": MAX_SESSIONS_PER_USER_DAY}}],
        },
        {"$inc": {key: 1}},
    )
    return before is not None


def _refund_failed_token(db, email: str, key: str) -> None:
    try:
        db.users.update_one({"email": email.lower(), key: {"$gt": 0}}, {"$inc": {key: -1}})
    except Exception:
        # A failed refund is safe in the direction of reduced access/spending.
        pass


def create_voice_router(current_user, user_doc, require_db) -> APIRouter:
    router = APIRouter()

    @router.post("/api/realtime/client-secret")
    def create_voice_secret(
        options: VoiceRequest,
        request: Request,
        user: str = Depends(current_user),
        origin: str | None = Header(default=None),
    ):
        response_headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
        if not realtime_enabled():
            raise HTTPException(status_code=503, detail="Realtime voice is not enabled.")
        validate_origin(origin)
        # current_user must be a valid signed-in account with a DB entry.
        account = user_doc(user)
        if account.get("disabled") or account.get("active") is False:
            raise HTTPException(status_code=403, detail="Account not available.")
        db = require_db()
        usage_key = _usage_key()
        if not _reserve_daily_token(db, user, usage_key):
            raise HTTPException(status_code=429, detail="Today's preview voice-session allowance has been reached.")
        api_key = os.getenv("OPENAI_API_KEY")
        salt = os.getenv("JWT_SECRET", "")
        safety_identifier = hashlib.sha256((salt + ":" + user.lower()).encode("utf-8")).hexdigest()

        payload = {
            "expires_after": {"anchor": "created_at", "seconds": SECRET_TTL_SECONDS},
            "session": {
                "type": "realtime",
                "model": VOICE_MODEL,
                "instructions": _instructions(options.mode, options.language),
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "transcription": {"model": "gpt-transcribe", "language": "es" if options.language == "Spanish" else "en"},
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {"voice": "marin"},
                },
                "tools": [],
                "tool_choice": "none",
            },
        }
        try:
            upstream = requests.post(
                VOICE_PROVIDER_URL,
                json=payload,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                    "OpenAI-Safety-Identifier": safety_identifier,
                },
                timeout=15,
            )
            upstream.raise_for_status()
            result = upstream.json()
            if not isinstance(result.get("value"), str) or not result["value"].startswith("ek_"):
                raise ValueError("Unexpected provider credential response")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            _refund_failed_token(db, user, usage_key)
            # Never expose provider errors or secrets in response or logs.
            raise HTTPException(status_code=502, detail="Voice connection is temporarily unavailable.")

        return JSONResponse(
            {
                "value": result["value"],
                "expires_at": result.get("expires_at"),
                "model": VOICE_MODEL,
                "max_preview_seconds": 180,
                "note": "Session is not recorded by WrenchRelay. Browser speech may be processed by OpenAI.",
            },
            headers=response_headers,
        )

    return router
