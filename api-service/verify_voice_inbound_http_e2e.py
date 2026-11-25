"""Isolated HTTP acceptance test for Rivit's inbound Twilio voice path.

Exercises the real FastAPI app over real HTTP with fictional tenants and a
locally computed Twilio signature. No Twilio account, no telephone call, no
OpenAI call, no customer data, no cost.

MongoDB selection:
  * WR_QA_MONGO_URL set  -> use that loopback server (CI service container).
  * otherwise            -> start a private throwaway mongod on a free port and
                            assert the server really bound the port we asked for.

Usage:
    WR_QA_ALLOW_LOCAL_MONGO=1 python api-service/verify_voice_inbound_http_e2e.py
"""
import base64
import hashlib
import hmac
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:18766"
DEFAULT_MONGO_PORT = 27017
DB_NAME = "wrenchrelay_voice_qa_isolated"
AUTH_TOKEN = "voice-qa-only-auth-token-not-real"
BRIDGE_KEY = "voice-qa-only-bridge-key-not-real"
GREETING = "Hi, I'm Rivit. You've reached Griffin Muffler & Brake Center. How can I help you today?"
TENANT_NUMBER = "+15555550100"
OPERATOR = "qa-voice-owner@example.com"

TENANTS = {
    TENANT_NUMBER: {
        "tenant_id": "griffin-muffler",
        "shop_name": "Griffin Muffler & Brake Center",
        "greeting": GREETING,
        "operator_emails": [OPERATOR],
        "recording": "disclosure",
    },
    "+15555550200": {
        "tenant_id": "other-test-shop",
        "shop_name": "Other Test Shop",
        "greeting": "Hi, I'm Rivit. You've reached Other Test Shop.",
        "operator_emails": ["qa-other-owner@example.com"],
        "recording": "none",
    },
}


def checked(condition, description):
    if not condition:
        raise AssertionError(description)
    print("PASS:", description, flush=True)


def free_tcp_port():
    """Ask the OS for an unused loopback port, never the well-known Mongo port."""
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        if port != DEFAULT_MONGO_PORT:
            return port
    raise RuntimeError("Could not obtain a non-default ephemeral TCP port")


def provision_mongo():
    """Return (mongo_url, ownership handle). Handle is None for external servers."""
    external = os.getenv("WR_QA_MONGO_URL", "").strip()
    if external:
        checked(
            external.startswith(("mongodb://127.0.0.1", "mongodb://localhost")),
            "external MongoDB URL is loopback-only (no remote or production database)",
        )
        print(f"INFO: using supplied loopback MongoDB at {external}", flush=True)
        return external, None

    from pymongo_inmemory import MongoClient as ThrowawayMongo

    port = free_tcp_port()
    # pymongo_inmemory otherwise inherits its configured default port, which is
    # how this harness previously reported 127.0.0.1:27017 instead of its own.
    client = ThrowawayMongo(port=port)
    bound = client.address
    checked(bound is not None, "throwaway MongoDB reported a bound address")
    checked(
        bound[1] == port,
        f"throwaway MongoDB bound the requested ephemeral port {port} (reported {bound[1]})",
    )
    checked(bound[1] != DEFAULT_MONGO_PORT, "throwaway MongoDB avoided the shared default port 27017")
    print(f"INFO: private throwaway MongoDB on 127.0.0.1:{bound[1]}", flush=True)
    return f"mongodb://127.0.0.1:{bound[1]}", client


def sign(path, params):
    material = BASE + path
    for name in sorted(params):
        material += name + str(params[name])
    digest = hmac.new(AUTH_TOKEN.encode(), material.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def start_api(mongo_url):
    env = os.environ.copy()
    env.update({
        "MONGO_URL": mongo_url,
        "DB_NAME": DB_NAME,
        "JWT_SECRET": "voice-qa-only-fake-jwt-key-20261125",
        "OPENAI_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
        "STRIPE_SECRET_KEY_LIVE": "",
        "GOOGLE_CLIENT_ID": "",
        "FRONTEND_URL": BASE,
        "CORS_ORIGINS": BASE,
        "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
        "TWILIO_PUBLIC_BASE_URL": BASE,
        "WRENCHRELAY_VOICE_TENANTS": json.dumps(TENANTS),
        "WRENCHRELAY_VOICE_INBOUND_ENABLED": "true",
        "WRENCHRELAY_VOICE_LIVE_APPROVED": "false",
        "WRENCHRELAY_VOICE_STREAM_URL": "",
        "WRENCHRELAY_VOICE_BRIDGE_KEY": BRIDGE_KEY,
        "PYTHONUNBUFFERED": "1",
    })
    path = Path(__file__).resolve().parent
    log = open(path.parent / "voice-qa-server.log", "ab")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "18766", "--no-access-log"],
        env=env, cwd=path, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    for _ in range(120):
        if proc.poll() is not None:
            raise RuntimeError("API exited before startup; see voice-qa-server.log")
        try:
            response = httpx.get(BASE + "/api/health", timeout=0.8)
            if response.status_code == 200 and response.json().get("database") == "ok":
                return proc
        except (httpx.RequestError, ValueError):
            pass
        time.sleep(0.25)
    terminate(proc)
    raise RuntimeError("Local voice QA API did not become database-ready")


def terminate(proc):
    if not proc or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate(timeout=5)


def main():
    import pymongo

    checked(os.getenv("WR_QA_ALLOW_LOCAL_MONGO") == "1", "local-only MongoDB opted in explicitly")
    mongo_url, owned = provision_mongo()
    admin_client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=4000)
    admin_client.admin.command("ping")
    database = admin_client[DB_NAME]
    checked(DB_NAME not in admin_client.list_database_names(), "isolated database starts absent")

    proc = None
    try:
        proc = start_api(mongo_url)

        health = httpx.get(BASE + "/api/voice/health").json()
        checked(health["inbound_enabled"] is True, "inbound voice enabled by explicit flag")
        checked(health["live_approved"] is False, "live audio NOT approved (paid path stays closed)")
        checked(health["signature_auth_configured"] is True, "webhook signature secret is configured")
        checked(health["tenants_valid"] and health["tenant_count"] == 2, "two fictional tenants parsed and valid")
        checked(AUTH_TOKEN not in json.dumps(health), "health endpoint exposes no secret")

        unsigned = httpx.post(BASE + "/api/voice/incoming", data={"CallSid": "CA-unsigned", "To": TENANT_NUMBER})
        checked(unsigned.status_code == 403, "unsigned inbound webhook rejected 403")
        checked("Rivit" not in unsigned.text, "rejected webhook returns no greeting or shop name")

        unknown_form = {"CallSid": "CA-unknown", "From": "+15555550999", "To": "+15555559999", "CallStatus": "ringing"}
        unknown = httpx.post(BASE + "/api/voice/incoming", data=unknown_form,
                             headers={"X-Twilio-Signature": sign("/api/voice/incoming", unknown_form)})
        checked(unknown.status_code == 200, "call to an unmapped number is answered with TwiML, not an error")
        checked("Rivit" not in unknown.text, "unmapped number never reaches the AI receptionist")

        call_form = {"CallSid": "CA-real-flow-1", "From": "+15555550999", "To": TENANT_NUMBER, "CallStatus": "ringing"}
        signature = sign("/api/voice/incoming", call_form)
        first = httpx.post(BASE + "/api/voice/incoming", data=call_form, headers={"X-Twilio-Signature": signature})
        checked(first.status_code == 200, "signed inbound call accepted over HTTP")
        checked("Griffin Muffler &amp; Brake Center" in first.text, "correct shop-specific greeting returned, TwiML-escaped")
        checked("Hi, I'm Rivit" in first.text, "greeting opens with the required Rivit wording")
        checked("<Hangup/>" in first.text, "hold mode ends the call cleanly")
        checked("<Record" not in first.text, "no recording is started by the application")
        checked("<Dial" not in first.text, "no transfer or outbound dial is attempted")

        replay = httpx.post(BASE + "/api/voice/incoming", data=call_form, headers={"X-Twilio-Signature": signature})
        checked(replay.text == first.text, "duplicate Twilio delivery returns the identical TwiML")

        def call_records():
            return list(database.voice_calls.find({"call_sid": "CA-real-flow-1"}))

        checked(len(call_records()) == 1, "duplicate delivery created only one call record")

        for state in ("in-progress", "completed", "completed"):
            callback = {"CallSid": "CA-real-flow-1", "CallStatus": state}
            response = httpx.post(BASE + "/api/voice/status", data=callback,
                                  headers={"X-Twilio-Signature": sign("/api/voice/status", callback)})
            checked(response.status_code == 200, f"status callback accepted: {state}")
        record = call_records()[0]
        checked(record["last_status"] == "completed", "latest call status persisted")
        checked(sorted(record["status_history"]) == ["completed", "in-progress"], "repeated status applied once")

        intake_payload = {
            "tenant_id": "griffin-muffler",
            "call_sid": "CA-real-flow-1",
            "fields": {
                "caller_name": "QA Fictional Caller",
                "callback_number": "+15555550123",
                "vehicle_year": "2016",
                "vehicle_make": "Honda",
                "vehicle_model": "Accord",
                "service_request": "Grinding noise when braking at low speed",
            },
        }
        saved = httpx.post(BASE + "/api/voice/intake", json=intake_payload,
                           headers={"X-Rivit-Bridge-Key": BRIDGE_KEY})
        checked(saved.status_code == 200, "structured intake saved through the bridge")
        checked(saved.json()["fields"]["vehicle_model"] == "Accord", "intake persisted the caller-supplied vehicle")
        checked("quantity" not in saved.text.lower(), "no invented fields were added to the intake")

        invented = dict(intake_payload)
        invented["fields"] = {**intake_payload["fields"], "price": "$149"}
        refused = httpx.post(BASE + "/api/voice/intake", json=invented, headers={"X-Rivit-Bridge-Key": BRIDGE_KEY})
        checked(refused.status_code == 422, "intake that asserts a price is refused")

        operator = httpx.Client(base_url=BASE, timeout=12)
        registered = operator.post("/api/auth/register", json={
            "email": OPERATOR, "name": "QA Voice Owner", "password": "Qa-Voice-Only-Password-2246!",
        })
        checked(registered.status_code == 200, "fictional shop operator registered")
        operator.headers["Authorization"] = "Bearer " + registered.json()["token"]

        own = operator.get("/api/voice/intakes", params={"tenant_id": "griffin-muffler"})
        checked(own.status_code == 200 and own.json()[0]["fields"]["caller_name"] == "QA Fictional Caller",
                "authorized operator can read the shop's intake record")
        checked(own.headers.get("cache-control") == "no-store", "intake responses are not cached")

        cross = operator.get("/api/voice/intakes", params={"tenant_id": "other-test-shop"})
        checked(cross.status_code == 403, "operator cannot read another shop's intakes")
        anonymous = httpx.get(BASE + "/api/voice/intakes", params={"tenant_id": "griffin-muffler"})
        checked(anonymous.status_code == 401, "unauthenticated intake read rejected")
        checked(httpx.get(BASE + "/api/me").status_code == 401, "staff endpoints still require sign-in")

        terminate(proc)
        proc = None
        proc = start_api(mongo_url)
        checked(len(call_records()) == 1, "call record survived a real backend process restart")
        checked(httpx.get(BASE + "/api/voice/health").json()["inbound_enabled"] is True,
                "voice configuration reloaded after restart")
        intakes_after = list(database.voice_intakes.find({"call_sid": "CA-real-flow-1"}))
        checked(len(intakes_after) == 1, "intake record survived a real backend process restart")
        checked(intakes_after[0]["fields"]["caller_name"] == "QA Fictional Caller",
                "intake content intact after restart")

        print("ISOLATED RIVIT INBOUND VOICE HTTP E2E PASS", flush=True)
    finally:
        terminate(proc)
        admin_client.drop_database(DB_NAME)
        admin_client.close()
        if owned is not None:
            owned.close()


if __name__ == "__main__":
    main()
