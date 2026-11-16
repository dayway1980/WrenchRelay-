"""Review-only OpenAI Realtime voice session broker.

Do not mount in production until provider credentials, origin policy,
and deployed source parity are verified.
The client never receives the server API key.
"""
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from backend.security import get_current_user, require_organization

router = APIRouter(prefix="/api/realtime", tags=["voice"])

class VerifiedPrincipal(BaseModel):
    user_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)

async def require_verified_principal(
    organization_id: str,
    user: dict = Depends(get_current_user),
) -> VerifiedPrincipal:
    await require_organization(user, organization_id, "assistant:use")
    return VerifiedPrincipal(user_id=user["id"], tenant_id=organization_id)

async def enforce_voice_quota(principal: VerifiedPrincipal) -> None:
    # Authenticated members can use voice without customer-facing credits.
    # Add cost monitoring and abuse detection separately, without blocking access.
    return None


def verify_browser_origin(request: Request) -> None:
    # Cookie-based browser sessions require an explicitly trusted origin.
    # No Origin on a cookie-authenticated request is rejected to prevent CSRF.
    allowed = {value.strip() for value in os.getenv("WR_VOICE_ALLOWED_ORIGINS", "").split(",") if value.strip()}
    origin = request.headers.get("origin")
    cookie_auth = "wr_access" in request.cookies
    if (origin and origin not in allowed) or (cookie_auth and not origin):
        raise HTTPException(status_code=403, detail="Voice request origin not permitted")

@router.post("/{organization_id}/session")
async def create_session(
    organization_id: str,
    request: Request,
    principal: VerifiedPrincipal = Depends(require_verified_principal),
) -> dict[str, Any]:
    verify_browser_origin(request)
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
