"""Review-only OpenAI Realtime voice session broker.

Do not mount in production until identity, tenant membership, CSRF/origin,
distributed rate limiting, provider credentials, and deployment parity are verified.
The client never receives the server API key.
"""
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/realtime", tags=["voice"])

class VerifiedPrincipal(BaseModel):
    user_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)

async def require_verified_principal(request: Request) -> VerifiedPrincipal:
    # Intentionally fail closed. Integrate the existing server-side auth and
    # tenant-membership verifier; NEVER trust user_id/tenant_id from request body.
    raise HTTPException(status_code=403, detail="Voice authentication not commissioned")

async def enforce_voice_quota(principal: VerifiedPrincipal) -> None:
    # Replace with atomic distributed per-user AND per-tenant quotas.
    raise HTTPException(status_code=429, detail="Voice rate limiting not commissioned")

@router.post("/session")
async def create_session(
    request: Request,
    principal: VerifiedPrincipal = Depends(require_verified_principal),
) -> dict[str, Any]:
    await enforce_voice_quota(principal)
    if os.getenv("WR_VOICE_COMMISSIONED") != "true":
        raise HTTPException(status_code=503, detail="Voice commissioning incomplete")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Voice provider not configured")
    # Provider API shape and model must be checked against the currently supported
    # OpenAI Realtime API before this endpoint is enabled.
    model = os.getenv("WR_REALTIME_MODEL", "gpt-realtime")
    payload = {"session": {"type": "realtime", "model": model, "audio": {"output": {"voice": "marin"}}}}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Voice provider unavailable")
    secret = data.get("value")
    if not isinstance(secret, str) or not secret:
        raise HTTPException(status_code=502, detail="Provider did not issue a session credential")
    return {"client_secret": secret, "expires_at": data.get("expires_at")}
