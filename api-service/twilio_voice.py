"""Inbound Twilio voice gateway for Rivit, WrenchRelay's automotive receptionist.

Design rules enforced here:
  * No credential ever appears in a response, a log line or TwiML.
  * Every inbound request must carry a valid ``X-Twilio-Signature``.
  * An unknown dialed number is never answered by an AI agent.
  * The shop greeting is configuration, never generated text, so the agent cannot
    invent a shop name, hours, services, prices, availability or appointments.
  * Intake records accept only facts a caller actually supplied. Price, quote,
    hours and confirmed-appointment fields are structurally rejected.
  * Nothing here places an outbound call, buys a number, dials a transfer or
    starts a recording. Live audio is emitted only when a deployment flag AND a
    media-stream URL are both present.

Signature reference: Twilio signs form-encoded webhooks with HMAC-SHA1 over the
exact public URL followed by the alphabetically sorted POST parameter names and
values, Base64 encoded, keyed by the account Auth Token. A Twilio API Key SID and
secret cannot validate this header. Twilio's Webhooks configuration API can
instead sign with an operator-managed shared key (HMAC-SHA256 or HMAC-SHA1).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from xml.sax.saxutils import escape, quoteattr

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pymongo.errors import DuplicateKeyError

E164 = re.compile(r"^\+[1-9]\d{6,14}$")
TWILIO_WEBHOOK_PATHS = ("/api/voice/incoming", "/api/voice/status", "/api/voice/intake")

# Keys a tenant record may contain. Anything else is a configuration error, so a
# stray "hours", "prices" or "appointment" block can never reach the caller.
TENANT_ALLOWED_KEYS = {
    "tenant_id",
    "shop_name",
    "greeting",
    "transfer_number",
    "operator_emails",
    "recording",
    "timezone",
}
# Explicitly refused even though they might look reasonable: the assistant must
# not state facts the shop has not published, and it must never book work.
TENANT_FORBIDDEN_KEYS = {
    "hours",
    "business_hours",
    "services",
    "service_menu",
    "prices",
    "pricing",
    "availability",
    "appointments",
    "appointment_confirmation",
    "diagnosis",
    "repair_estimate",
}

RECORDING_MODES = {"none", "disclosure"}

# Facts a caller may supply for an intake record.
INTAKE_ALLOWED_FIELDS = {
    "caller_name",
    "callback_number",
    "vehicle_year",
    "vehicle_make",
    "vehicle_model",
    "vehicle_vin",
    "service_request",
    "preferred_time_window",
    "notes",
    "transcript_summary",
}
# Values the assistant must never invent or promise on the shop's behalf.
INTAKE_FORBIDDEN_FIELDS = {
    "price",
    "quote",
    "estimate",
    "hours",
    "availability",
    "appointment",
    "appointment_confirmed",
    "confirmed_time",
    "diagnosis",
    "repair_completed",
}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


def signature_secret() -> tuple[bytes, str] | None:
    """Return (key, hashlib name) for webhook signature validation.

    Prefers an operator-managed shared key when configured, otherwise the
    account Auth Token. Returns None when nothing is configured so the caller
    fails closed instead of trusting unsigned traffic.
    """
    shared = os.getenv("TWILIO_WEBHOOK_SHARED_KEY", "").strip()
    if shared:
        algorithm = os.getenv("TWILIO_WEBHOOK_SIGNATURE_ALGORITHM", "sha256").strip().lower()
        if algorithm not in {"sha1", "sha256"}:
            return None
        return shared.encode("utf-8"), algorithm
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if token:
        return token.encode("utf-8"), "sha1"
    return None


def compute_signature(url: str, params: dict[str, Any], key: bytes, algorithm: str = "sha1") -> str:
    """Reproduce Twilio's documented signing string.

    Matches twilio-python's RequestValidator: sorted unique parameter names, and
    for each name every value sorted, concatenated with no delimiters.
    """
    payload = url
    for name in sorted(set(params)):
        value = params[name]
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in sorted({"" if v is None else str(v) for v in values}):
            payload += name + item
    digest = hmac.new(key, payload.encode("utf-8"), getattr(hashlib, algorithm)).digest()
    return base64.b64encode(digest).decode("utf-8").strip()


def verify_signature(
    url: str, params: dict[str, Any], signature: str | None, key: bytes, algorithm: str = "sha1"
) -> bool:
    if not signature:
        return False
    expected = compute_signature(url, params, key, algorithm)
    return hmac.compare_digest(expected, signature.strip())


def canonical_url(request: Request) -> str:
    """Rebuild the exact public URL Twilio signed.

    Twilio signs the URL configured on the number. Behind a proxy the ASGI URL
    can be an internal http://host:port, which would never match. Operators set
    TWILIO_PUBLIC_BASE_URL to the public https origin, and the request path is
    appended verbatim (including any query string).
    """
    base = os.getenv("TWILIO_PUBLIC_BASE_URL", "").strip().rstrip("/")
    path = request.url.path
    query = request.url.query
    if base:
        return f"{base}{path}" + (f"?{query}" if query else "")
    return str(request.url)


def load_tenants(raw: str | None = None) -> dict[str, dict]:
    """Parse and validate the dialed-number -> tenant registry."""
    source = os.getenv("WRENCHRELAY_VOICE_TENANTS", "") if raw is None else raw
    if not source.strip():
        return {}
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError("WRENCHRELAY_VOICE_TENANTS is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("WRENCHRELAY_VOICE_TENANTS must be an object keyed by E.164 number")
    tenants: dict[str, dict] = {}
    for number, config in parsed.items():
        if not E164.match(number):
            raise ValueError(f"tenant number {number!r} is not E.164")
        if not isinstance(config, dict):
            raise ValueError(f"tenant {number!r} must be an object")
        unknown = set(config) - TENANT_ALLOWED_KEYS
        if unknown:
            raise ValueError(f"tenant {number!r} has unsupported keys: {sorted(unknown)}")
        forbidden = set(config) & TENANT_FORBIDDEN_KEYS
        if forbidden:
            raise ValueError(
                f"tenant {number!r} may not configure inferred shop facts: {sorted(forbidden)}"
            )
        for required in ("tenant_id", "shop_name", "greeting"):
            if not str(config.get(required, "")).strip():
                raise ValueError(f"tenant {number!r} requires {required}")
        recording = str(config.get("recording", "none")).strip().lower()
        if recording not in RECORDING_MODES:
            raise ValueError(f"tenant {number!r} recording must be one of {sorted(RECORDING_MODES)}")
        emails = config.get("operator_emails") or []
        if not isinstance(emails, list) or not all(isinstance(x, str) for x in emails):
            raise ValueError(f"tenant {number!r} operator_emails must be a list of addresses")
        tenants[number] = {**config, "recording": recording,
                           "operator_emails": [x.strip().lower() for x in emails if x.strip()]}
    return tenants


def resolve_tenant(dialed: str | None, tenants: dict[str, dict]) -> dict | None:
    if not dialed:
        return None
    return tenants.get(dialed.strip())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _twiml(body: str) -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>',
        media_type="application/xml",
        headers={"Cache-Control": "no-store"},
    )


def _say(text: str) -> str:
    return f"<Say voice=\"Polly.Joanna\">{escape(text)}</Say>"


def hold_twiml(tenant: dict) -> str:
    """Greeting-only answer used until a live voice deployment is approved.

    States no hours, no services, no prices and takes no message, because none
    of those are known-safe to assert from configuration alone.
    """
    return (
        _say(tenant["greeting"])
        + _say("This automated assistant is still being tested and cannot take your details yet.")
        + _say("No message was recorded. Please call back and a team member will help you.")
        + "<Hangup/>"
    )


def live_twiml(tenant: dict, stream_url: str, call_sid: str) -> str:
    """Greeting, consent disclosure, then the duplex media stream.

    The greeting is spoken by Twilio from configuration, so the exact
    shop-specific wording is guaranteed even if the model misbehaves. The model
    receives only tenant identity and call identity, never customer records.
    """
    parts = [_say(tenant["greeting"])]
    if tenant.get("recording") == "disclosure":
        parts.append(_say("This call may be recorded so the shop can help you accurately."))
    parts.append(
        "<Connect><Stream url={url}>"
        "<Parameter name=\"tenant_id\" value={tenant}/>"
        "<Parameter name=\"shop_name\" value={shop}/>"
        "<Parameter name=\"call_sid\" value={sid}/>"
        "<Parameter name=\"recording\" value={rec}/>"
        "</Stream></Connect>".format(
            url=quoteattr(stream_url),
            tenant=quoteattr(tenant["tenant_id"]),
            shop=quoteattr(tenant["shop_name"]),
            sid=quoteattr(call_sid),
            rec=quoteattr(tenant.get("recording", "none")),
        )
    )
    return "".join(parts)


def unknown_number_twiml() -> str:
    return _say("Sorry, this number is not able to take automated calls. Goodbye.") + "<Hangup/>"


class MongoReplayStore:
    """Claim-once store. A unique _id makes duplicate deliveries observable."""

    def __init__(self, collection):
        self.collection = collection

    def ensure_indexes(self) -> None:
        # _id is unique already; this documents intent for the operator.
        try:
            self.collection.create_index("received_at")
        except Exception:  # pragma: no cover - index creation is best effort
            pass

    def claim(self, key: str, document: dict) -> bool:
        try:
            self.collection.insert_one({"_id": key, "received_at": _now(), **document})
            return True
        except DuplicateKeyError:
            return False


class MemoryReplayStore:
    """In-process equivalent used by the offline test suite only."""

    def __init__(self) -> None:
        self.keys: dict[str, dict] = {}

    def ensure_indexes(self) -> None:
        return None

    def claim(self, key: str, document: dict) -> bool:
        if key in self.keys:
            return False
        self.keys[key] = {"received_at": _now(), **document}
        return True


def _clean_number(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    return candidate if E164.match(candidate) else None


def validate_intake(payload: dict) -> dict:
    """Reject invented shop facts and unknown fields before persistence."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Intake payload must be an object.")
    forbidden = set(payload) & INTAKE_FORBIDDEN_FIELDS
    if forbidden:
        raise HTTPException(
            status_code=422,
            detail=(
                "Intake may not assert shop facts the caller did not supply: "
                + ", ".join(sorted(forbidden))
            ),
        )
    unknown = set(payload) - INTAKE_ALLOWED_FIELDS
    if unknown:
        raise HTTPException(status_code=422, detail="Unsupported intake fields: " + ", ".join(sorted(unknown)))
    cleaned: dict[str, Any] = {}
    for field, value in payload.items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"{field} must be text.")
        if len(value) > 2000:
            raise HTTPException(status_code=422, detail=f"{field} is too long.")
        text = value.strip()
        if text:
            cleaned[field] = text
    if "callback_number" in cleaned and not _clean_number(cleaned["callback_number"]):
        raise HTTPException(status_code=422, detail="callback_number must be E.164.")
    if not cleaned.get("service_request"):
        raise HTTPException(status_code=422, detail="service_request is required to record an intake.")
    return cleaned


def create_voice_inbound_router(
    require_db: Callable[[], Any],
    current_user: Callable[..., Any],
    admin_email: str = "",
) -> APIRouter:
    router = APIRouter(tags=["voice"])

    def _store():
        return MongoReplayStore(require_db().voice_webhook_events)

    def _authenticate(request: Request, params: dict[str, str], signature: str | None) -> None:
        credentials = signature_secret()
        if credentials is None:
            # Fail closed: unsigned traffic is never trusted, even in development.
            raise HTTPException(status_code=503, detail="Voice webhook authentication is not configured.")
        key, algorithm = credentials
        if not verify_signature(canonical_url(request), params, signature, key, algorithm):
            raise HTTPException(status_code=403, detail="Invalid voice webhook signature.")

    @router.post("/api/voice/incoming")
    async def voice_incoming(request: Request, x_twilio_signature: str | None = Header(default=None)):
        form = dict(await request.form())
        _authenticate(request, form, x_twilio_signature)
        if not _env_flag("WRENCHRELAY_VOICE_INBOUND_ENABLED"):
            raise HTTPException(status_code=503, detail="Inbound voice is not enabled.")

        call_sid = (form.get("CallSid") or "").strip()
        dialed = (form.get("To") or "").strip()
        if not call_sid:
            raise HTTPException(status_code=400, detail="Missing CallSid.")
        try:
            tenants = load_tenants()
        except ValueError:
            raise HTTPException(status_code=503, detail="Voice tenant configuration is invalid.")

        tenant = resolve_tenant(dialed, tenants)
        store = _store()
        first_delivery = store.claim(
            f"incoming:{call_sid}",
            {"kind": "incoming", "call_sid": call_sid, "to": dialed, "from": form.get("From")},
        )

        if tenant is None:
            # Unmapped number: refuse politely, record the attempt, no AI, no cost.
            if first_delivery:
                require_db().voice_calls.update_one(
                    {"call_sid": call_sid},
                    {"$set": {"call_sid": call_sid, "to": dialed, "from": form.get("From"),
                              "tenant_id": None, "outcome": "unmapped_number", "updated_at": _now()},
                     "$setOnInsert": {"created_at": _now()}},
                    upsert=True,
                )
            return _twiml(unknown_number_twiml())

        stream_url = os.getenv("WRENCHRELAY_VOICE_STREAM_URL", "").strip()
        live = _env_flag("WRENCHRELAY_VOICE_LIVE_APPROVED")
        if live and not stream_url.startswith("wss://"):
            # A live flag without a secure media endpoint must never answer with audio.
            live = False

        if first_delivery:
            require_db().voice_calls.update_one(
                {"call_sid": call_sid},
                {"$set": {"call_sid": call_sid, "to": dialed, "from": form.get("From"),
                          "tenant_id": tenant["tenant_id"], "shop_name": tenant["shop_name"],
                          "mode": "live" if live else "greeting_hold",
                          "recording": tenant.get("recording", "none"),
                          "outcome": "answered", "updated_at": _now()},
                 "$setOnInsert": {"created_at": _now()}},
                upsert=True,
            )

        body = live_twiml(tenant, stream_url, call_sid) if live else hold_twiml(tenant)
        return _twiml(body)

    @router.post("/api/voice/status")
    async def voice_status(request: Request, x_twilio_signature: str | None = Header(default=None)):
        form = dict(await request.form())
        _authenticate(request, form, x_twilio_signature)
        call_sid = (form.get("CallSid") or "").strip()
        status = (form.get("CallStatus") or "").strip()
        if not call_sid or not status:
            raise HTTPException(status_code=400, detail="Missing CallSid or CallStatus.")
        store = _store()
        # Twilio retries status callbacks; each (call, status) pair is applied once.
        store.claim(
            f"status:{call_sid}:{status}",
            {"kind": "status", "call_sid": call_sid, "status": status},
        )
        require_db().voice_calls.update_one(
            {"call_sid": call_sid},
            {"$set": {"call_sid": call_sid, "last_status": status, "updated_at": _now()},
             "$setOnInsert": {"created_at": _now()},
             "$addToSet": {"status_history": status}},
            upsert=True,
        )
        return {"received": True}

    @router.post("/api/voice/intake")
    async def voice_intake(request: Request, x_rivit_bridge_key: str | None = Header(default=None)):
        """Internal endpoint the media bridge calls once a caller's intake is complete.

        Authenticated with a dedicated bridge key, not the operator session, so a
        browser can never post intake text and a bridge key can never read records.
        """
        expected = os.getenv("WRENCHRELAY_VOICE_BRIDGE_KEY", "").strip()
        if not expected:
            raise HTTPException(status_code=503, detail="Voice bridge is not configured.")
        if not x_rivit_bridge_key or not hmac.compare_digest(x_rivit_bridge_key, expected):
            raise HTTPException(status_code=403, detail="Invalid bridge credential.")
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Intake payload must be an object.")
        tenant_id = str(payload.get("tenant_id", "")).strip()
        call_sid = str(payload.get("call_sid", "")).strip()
        if not tenant_id or not call_sid:
            raise HTTPException(status_code=422, detail="tenant_id and call_sid are required.")
        try:
            tenants = load_tenants()
        except ValueError:
            raise HTTPException(status_code=503, detail="Voice tenant configuration is invalid.")
        if tenant_id not in {t["tenant_id"] for t in tenants.values()}:
            raise HTTPException(status_code=403, detail="Unknown tenant.")
        fields = validate_intake(payload.get("fields") or {})
        db = require_db()
        record = {
            "tenant_id": tenant_id,
            "call_sid": call_sid,
            "fields": fields,
            "status": "complete" if fields.get("service_request") else "incomplete",
            "updated_at": _now(),
        }
        db.voice_intakes.update_one(
            {"tenant_id": tenant_id, "call_sid": call_sid},
            {"$set": record, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
        saved = db.voice_intakes.find_one({"tenant_id": tenant_id, "call_sid": call_sid}, {"_id": 0})
        return JSONResponse(saved, headers={"Cache-Control": "no-store"})

    def _authorized_tenant(user: str, tenant_id: str, tenants: dict[str, dict]) -> dict:
        tenant = next((t for t in tenants.values() if t["tenant_id"] == tenant_id), None)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Unknown tenant.")
        operator = user.strip().lower()
        allowed = operator in tenant.get("operator_emails", [])
        is_admin = bool(admin_email) and operator == admin_email
        if not (allowed or is_admin):
            raise HTTPException(status_code=403, detail="You do not operate this shop.")
        return tenant

    @router.get("/api/voice/intakes")
    def list_intakes(
        tenant_id: str = Query(min_length=1, max_length=120),
        limit: int = Query(default=50, ge=1, le=200),
        user: str = Depends(current_user),
    ):
        try:
            tenants = load_tenants()
        except ValueError:
            raise HTTPException(status_code=503, detail="Voice tenant configuration is invalid.")
        _authorized_tenant(user, tenant_id, tenants)
        docs = list(
            require_db().voice_intakes.find({"tenant_id": tenant_id}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return JSONResponse(docs, headers={"Cache-Control": "no-store"})

    @router.get("/api/voice/calls")
    def list_calls(
        tenant_id: str = Query(min_length=1, max_length=120),
        limit: int = Query(default=50, ge=1, le=200),
        user: str = Depends(current_user),
    ):
        try:
            tenants = load_tenants()
        except ValueError:
            raise HTTPException(status_code=503, detail="Voice tenant configuration is invalid.")
        _authorized_tenant(user, tenant_id, tenants)
        docs = list(
            require_db().voice_calls.find({"tenant_id": tenant_id}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return JSONResponse(docs, headers={"Cache-Control": "no-store"})

    @router.get("/api/voice/health")
    def voice_health():
        """Non-secret readiness report for an operator or a smoke test."""
        try:
            tenants = load_tenants()
            tenants_valid = True
        except ValueError:
            tenants, tenants_valid = {}, False
        credentials = signature_secret()
        return {
            "inbound_enabled": _env_flag("WRENCHRELAY_VOICE_INBOUND_ENABLED"),
            "live_approved": _env_flag("WRENCHRELAY_VOICE_LIVE_APPROVED"),
            "stream_configured": os.getenv("WRENCHRELAY_VOICE_STREAM_URL", "").startswith("wss://"),
            "signature_auth_configured": credentials is not None,
            "signature_algorithm": credentials[1] if credentials else None,
            "tenants_valid": tenants_valid,
            "tenant_count": len(tenants),
            "bridge_configured": bool(os.getenv("WRENCHRELAY_VOICE_BRIDGE_KEY", "").strip()),
        }

    return router
