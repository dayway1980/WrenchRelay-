"""Twilio Media Streams <-> OpenAI Realtime bridge for Rivit.

Off by default. A socket reaches this module only after the webhook gateway has
required ``WRENCHRELAY_VOICE_LIVE_APPROVED``, a ``wss://`` media URL and a bridge
key, and this module re-checks the flag, the per-call token, the tenant mapping,
the call identity and the OpenAI credential independently. Every failure closes
the socket; there is no unauthenticated or "log it and continue" path.

Audio is relayed, never stored or transcoded. Twilio sends 8 kHz G.711 mu-law as
base64 and the Realtime session is configured for ``audio/pcmu``, so each payload
travels unchanged in both directions. A call is also hard-capped in duration
(``WRENCHRELAY_VOICE_MAX_CALL_SECONDS``), so a stream that never gets a ``stop``
cannot keep billing indefinitely. The only thing written to the database is
the structured intake the caller actually supplied through the model's
``record_intake`` tool call, validated by the same rules the HTTP intake endpoint
uses. No transcript, no recording, no outbound call, no number purchase.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from twilio_voice import load_tenants, save_intake, utc_now, validate_intake, verify_stream_token

log = logging.getLogger("rivit.voice")

REALTIME_BASE = "wss://api.openai.com/v1/realtime"
DEFAULT_MODEL = "gpt-realtime"
DEFAULT_VOICE = "marin"
START_TIMEOUT_SECONDS = 15
DEFAULT_MAX_CALL_SECONDS = 600

# The model may only hand back fields the caller actually spoke. validate_intake
# enforces the same allow-list and refuses price/quote/hours/appointment keys.
INTAKE_TOOL = {
    "type": "function",
    "name": "record_intake",
    "description": (
        "Record what the caller told you. Call this once you know what the vehicle "
        "needs. Pass only values the caller actually gave; never guess a value and "
        "never pass a price, quote, hours, availability or an appointment."
    ),
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "caller_name": {"type": "string", "description": "Name the caller gave."},
            "callback_number": {"type": "string", "description": "Callback number in E.164, e.g. +15555550123."},
            "vehicle_year": {"type": "string"},
            "vehicle_make": {"type": "string"},
            "vehicle_model": {"type": "string"},
            "vehicle_vin": {"type": "string"},
            "service_request": {"type": "string", "description": "What the vehicle is doing, in the caller's words."},
            "preferred_time_window": {"type": "string", "description": "When the caller said they can come in."},
            "notes": {"type": "string"},
            "transcript_summary": {"type": "string", "description": "One or two sentences summarising the call."},
        },
        "required": ["service_request"],
    },
}


def live_approved() -> bool:
    return os.getenv("WRENCHRELAY_VOICE_LIVE_APPROVED", "").strip().lower() == "true"


def realtime_model() -> str:
    return os.getenv("WRENCHRELAY_VOICE_MODEL", "").strip() or DEFAULT_MODEL


def realtime_voice() -> str:
    return os.getenv("WRENCHRELAY_VOICE_NAME", "").strip() or DEFAULT_VOICE


def realtime_endpoint() -> str:
    return f"{REALTIME_BASE}?model={quote(realtime_model())}"


def max_call_seconds() -> float:
    """Ceiling on one live call. Junk, zero, negative or infinite falls back to the default."""
    raw = os.getenv("WRENCHRELAY_VOICE_MAX_CALL_SECONDS", "").strip()
    try:
        seconds = float(raw)
    except ValueError:
        return float(DEFAULT_MAX_CALL_SECONDS)
    return seconds if math.isfinite(seconds) and seconds > 0 else float(DEFAULT_MAX_CALL_SECONDS)


def build_instructions(tenant: dict) -> str:
    """Ground the model in tenant configuration only.

    The shop's name and greeting are the only shop-specific facts available, and
    the rules refuse everything the shop has not published. Hours, prices,
    availability and appointments are deliberately absent, not merely discouraged.
    """
    return (
        f"You are Rivit, the phone assistant for {tenant['shop_name']}. "
        f"The caller has already heard this greeting: \"{tenant['greeting']}\" Do not repeat it.\n"
        "Rules you must follow:\n"
        "- Speak in short, plain sentences. Ask exactly one question at a time.\n"
        "- Discuss only what the caller tells you. Never state or guess the shop's hours, prices, "
        "availability, diagnosis or appointment times, and never confirm a booking.\n"
        "- If the caller asks about hours, price, availability or an appointment, say a team member "
        "will follow up.\n"
        "- Collect the caller's name, a callback number, the vehicle year, make and model, what the "
        "vehicle is doing, and when they can bring it in.\n"
        "- Call record_intake once you have what the vehicle needs, and again only if the caller "
        "corrects something. Never invent a value for a field the caller did not give.\n"
        "- If the caller asks for a person, record the intake and say a team member will call back.\n"
    )


def session_update(tenant: dict) -> dict:
    """GA Realtime session config for a telephone call.

    ``audio/pcmu`` is the GA name for G.711 mu-law, which is exactly what Twilio
    sends and expects, so no resampling or codec bridge is needed. Output is
    capped so a single reply cannot run long on the caller's line.
    """
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": realtime_model(),
            "instructions": build_instructions(tenant),
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {"type": "server_vad", "silence_duration_ms": 700},
                },
                "output": {"format": {"type": "audio/pcmu"}, "voice": realtime_voice()},
            },
            "tools": [INTAKE_TOOL],
            "tool_choice": "auto",
            "max_output_tokens": 400,
        },
    }


class BridgeSession:
    """Frame translator. Pure: no sockets, no clock, no database, no audio decoding."""

    def __init__(self, stream_sid: str):
        self.stream_sid = stream_sid

    def from_twilio(self, event: dict) -> list[dict]:
        media = event.get("media") or {}
        if event.get("event") != "media" or media.get("track", "inbound") != "inbound":
            return []
        payload = media.get("payload")
        if not payload:
            return []
        return [{"type": "input_audio_buffer.append", "audio": payload}]

    def from_realtime(self, event: dict) -> list[dict]:
        kind = event.get("type")
        if kind == "response.output_audio.delta" and event.get("delta"):
            return [{"event": "media", "streamSid": self.stream_sid, "media": {"payload": event["delta"]}}]
        if kind == "input_audio_buffer.speech_started":
            # Caller interrupted: drop audio Twilio has queued but not yet played.
            return [{"event": "clear", "streamSid": self.stream_sid}]
        return []


def parse_intake_call(event: dict) -> tuple[str, dict | None, str | None]:
    """Return (call_id, validated fields, refusal reason).

    Never raises on model output: a malformed or invented tool call is refused and
    reported back to the model instead of being stored or crashing the stream.
    """
    call_id = str(event.get("call_id") or "").strip()
    if event.get("name") != INTAKE_TOOL["name"]:
        return call_id, None, "unknown_tool"
    try:
        arguments = json.loads(event.get("arguments") or "{}")
    except (TypeError, ValueError):
        return call_id, None, "arguments were not valid JSON"
    if not isinstance(arguments, dict):
        return call_id, None, "arguments were not an object"
    try:
        return call_id, validate_intake(arguments), None
    except HTTPException as exc:
        return call_id, None, str(exc.detail)[:300]


def tool_result(call_id: str, recorded: bool) -> list[dict]:
    """Answer the tool call so the model can keep talking."""
    if recorded:
        output = {"recorded": True}
    else:
        output = {
            "recorded": False,
            "note": "Not recorded. Tell the caller a team member will follow up and promise no time.",
        }
    return [
        {
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "call_id": call_id, "output": json.dumps(output)},
        },
        {"type": "response.create"},
    ]


async def record_tool_call(event: dict, db, tenant: dict, call_sid: str) -> list[dict]:
    call_id, fields, reason = parse_intake_call(event)
    recorded = False
    if fields is not None:
        try:
            # pymongo is blocking; keep it off the audio loop.
            await asyncio.to_thread(save_intake, db, tenant["tenant_id"], call_sid, fields)
            recorded = True
        except Exception:
            reason = "intake store unavailable"
    if not recorded:
        log.warning("call %s intake not recorded: %s", call_sid, reason)
    return tool_result(call_id, recorded) if call_id else []


async def connect_realtime_api(url: str, api_key: str):
    """Open the Realtime socket with the server-side credential header."""
    from websockets.asyncio.client import connect

    return await connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        max_size=4 * 2**20,
        ping_interval=20,
        close_timeout=5,
        open_timeout=10,
    )


def _mark(db, call_sid: str, state: str) -> None:
    try:
        db.voice_calls.update_one(
            {"call_sid": call_sid},
            {"$set": {"call_sid": call_sid, "media_stream": state, "updated_at": utc_now()}},
        )
    except Exception:
        log.warning("call %s could not record media stream state", call_sid)


async def _await_start(websocket: WebSocket) -> dict | None:
    """Read Twilio's connect/start preamble under one deadline; anything else is ignored."""

    async def read_preamble() -> dict | None:
        for _ in range(20):
            try:
                event = json.loads(await websocket.receive_text())
            except ValueError:
                continue
            if event.get("event") == "start":
                return event.get("start") or {}
            if event.get("event") == "stop":
                return None
        return None

    return await asyncio.wait_for(read_preamble(), timeout=START_TIMEOUT_SECONDS)


def create_voice_stream_router(require_db, connect_realtime=None) -> APIRouter:
    router = APIRouter(tags=["voice"])
    connector = connect_realtime or connect_realtime_api

    async def refuse(websocket: WebSocket, reason: str) -> None:
        log.warning("voice stream refused: %s", reason)
        try:
            await websocket.close(code=1008, reason="Voice stream not authorized.")
        except RuntimeError:
            pass

    @router.websocket("/api/voice/stream")
    async def voice_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        call_sid = (websocket.query_params.get("call_sid") or "").strip()
        if not live_approved():
            return await refuse(websocket, "live audio is not approved")
        if not verify_stream_token(call_sid, websocket.query_params.get("token")):
            return await refuse(websocket, "per-call stream token missing or invalid")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return await refuse(websocket, "OpenAI credential is not configured")

        try:
            start = await _await_start(websocket)
        except (asyncio.TimeoutError, WebSocketDisconnect):
            return await refuse(websocket, "media stream did not start")
        if not start:
            return await refuse(websocket, "media stream did not start")

        stream_sid = str(start.get("streamSid") or "")
        params = {str(k): str(v) for k, v in (start.get("customParameters") or {}).items()}
        try:
            tenants = load_tenants()
        except ValueError:
            return await refuse(websocket, "tenant configuration is invalid")
        tenant = next((t for t in tenants.values() if t["tenant_id"] == params.get("tenant_id")), None)
        if tenant is None or not stream_sid:
            return await refuse(websocket, "dialed tenant is not allow-listed")
        if params.get("call_sid") != call_sid:
            return await refuse(websocket, "stream call identity does not match its token")

        try:
            db = require_db()
            db.voice_calls.update_one(
                {"call_sid": call_sid},
                {"$set": {"call_sid": call_sid, "tenant_id": tenant["tenant_id"],
                          "shop_name": tenant["shop_name"], "media_stream": "connected",
                          "updated_at": utc_now()},
                 "$setOnInsert": {"created_at": utc_now()}},
                upsert=True,
            )
        except Exception:
            return await refuse(websocket, "call record store is unavailable")

        try:
            upstream = await connector(realtime_endpoint(), api_key)
        except Exception as exc:
            log.warning("voice stream upstream connect failed: %s", type(exc).__name__)
            return await refuse(websocket, "voice assistant unavailable")

        session = BridgeSession(stream_sid)
        limit = max_call_seconds()
        ended_by = "ended"

        async def call_deadline(seconds: float) -> None:
            # Twilio ends the call when its media socket closes, so this is the
            # ceiling on what a single call can spend on the Realtime model.
            nonlocal ended_by
            await asyncio.sleep(seconds)
            ended_by = "max_duration"
            log.warning("call %s ended at the %gs media bridge call limit", call_sid, seconds)

        async def twilio_to_realtime() -> None:
            while True:
                try:
                    event = json.loads(await websocket.receive_text())
                except ValueError:
                    continue
                if event.get("event") == "stop":
                    return
                for frame in session.from_twilio(event):
                    await upstream.send(json.dumps(frame))

        async def realtime_to_twilio() -> None:
            async for raw in upstream:
                try:
                    event = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                if event.get("type") == "response.function_call_arguments.done":
                    for frame in await record_tool_call(event, db, tenant, call_sid):
                        await upstream.send(json.dumps(frame))
                    continue
                for frame in session.from_realtime(event):
                    await websocket.send_json(frame)

        try:
            await upstream.send(json.dumps(session_update(tenant)))
            tasks = [
                asyncio.create_task(twilio_to_realtime()),
                asyncio.create_task(realtime_to_twilio()),
                asyncio.create_task(call_deadline(limit)),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)
        finally:
            try:
                await upstream.close()
            except Exception:
                pass
            _mark(db, call_sid, ended_by)
            try:
                await websocket.close()
            except RuntimeError:
                pass

    return router
