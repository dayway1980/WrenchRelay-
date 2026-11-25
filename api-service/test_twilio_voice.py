"""Offline, no-cost tests for the inbound Twilio voice gateway.

No Twilio account, no OpenAI call, no network, no database. Every request is
signed locally with the same documented algorithm Twilio uses, so the failure
paths (tampering, replay, unknown tenant, proxy URL mismatch) are all exercised
without spending money or touching a customer.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import twilio_voice
from twilio_voice import create_voice_inbound_router, load_tenants

BASE = "https://api.example.test"
INCOMING = "/api/voice/incoming"
STATUS = "/api/voice/status"
INTAKE = "/api/voice/intake"

AUTH_TOKEN = "test-auth-token-not-real-0000"
BRIDGE_KEY = "test-bridge-key-not-real-1111"
GREETING = "Hi, I'm Rivit. You've reached Griffin Muffler & Brake Center. How can I help you today?"

TENANTS = {
    "+15555550100": {
        "tenant_id": "griffin-muffler",
        "shop_name": "Griffin Muffler & Brake Center",
        "greeting": GREETING,
        "operator_emails": ["owner@griffin.example"],
        "recording": "disclosure",
    },
    "+15555550200": {
        "tenant_id": "second-shop",
        "shop_name": "Second Shop",
        "greeting": "Hi, I'm Rivit. You've reached Second Shop.",
        "operator_emails": ["owner@second.example"],
        "recording": "none",
    },
}


def sign(url: str, params: dict, key: str = AUTH_TOKEN) -> str:
    """Independent re-implementation of Twilio's signing string."""
    material = url
    for name in sorted(params):
        value = params[name]
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in sorted({str(v) for v in values}):
            material += name + item
    digest = hmac.new(key.encode("utf-8"), material.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=-1):
        self.docs.sort(key=lambda d: str(d.get(key, "")), reverse=direction < 0)
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    def __iter__(self):
        return iter(self.docs)


class FakeCollection:
    def __init__(self):
        self.docs = []

    def create_index(self, *args, **kwargs):
        return "index"

    def _matches(self, doc, query):
        return all(doc.get(key) == value for key, value in query.items() if not key.startswith("$"))

    def insert_one(self, doc):
        if any(d.get("_id") == doc.get("_id") for d in self.docs):
            from pymongo.errors import DuplicateKeyError
            raise DuplicateKeyError("duplicate key")
        self.docs.append(deepcopy(doc))

    def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                for key, value in update.get("$addToSet", {}).items():
                    current = doc.setdefault(key, [])
                    if value not in current:
                        current.append(value)
                return
        if not upsert:
            return
        fresh = dict(query)
        fresh.update(update.get("$setOnInsert", {}))
        fresh.update(update.get("$set", {}))
        for key, value in update.get("$addToSet", {}).items():
            fresh[key] = [value]
        self.docs.append(fresh)

    def find_one(self, query, projection=None):
        for doc in self.docs:
            if self._matches(doc, query):
                return deepcopy(doc)
        return None

    def find(self, query, projection=None):
        return FakeCursor([deepcopy(d) for d in self.docs if self._matches(d, query)])


class FakeDb:
    def __init__(self):
        self.voice_webhook_events = FakeCollection()
        self.voice_calls = FakeCollection()
        self.voice_intakes = FakeCollection()


def build(db, operator="owner@griffin.example", authenticated=True):
    app = FastAPI()

    def current_user():
        if not authenticated:
            raise HTTPException(status_code=401, detail="Sign in required.")
        return operator

    app.include_router(create_voice_inbound_router(lambda: db, current_user, "admin@wrenchrelay.example"))
    return TestClient(app)


ENV = {
    "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
    "TWILIO_PUBLIC_BASE_URL": BASE,
    "WRENCHRELAY_VOICE_TENANTS": json.dumps(TENANTS),
    "WRENCHRELAY_VOICE_INBOUND_ENABLED": "true",
    "WRENCHRELAY_VOICE_LIVE_APPROVED": "false",
    "WRENCHRELAY_VOICE_STREAM_URL": "",
    "WRENCHRELAY_VOICE_BRIDGE_KEY": BRIDGE_KEY,
    "TWILIO_WEBHOOK_SHARED_KEY": "",
}


def incoming_form(**overrides):
    form = {
        "CallSid": "CA00000000000000000000000000000001",
        "AccountSid": "AC00000000000000000000000000000001",
        "From": "+15555550999",
        "To": "+15555550100",
        "CallStatus": "ringing",
        "Direction": "inbound",
        "NumSegments": "1",
    }
    form.update(overrides)
    return form


def post_signed(client, path, form, env=None, key=AUTH_TOKEN, tamper=False):
    url = BASE + path
    signature = sign(url, form, key)
    headers = {"X-Twilio-Signature": signature}
    payload = dict(form)
    if tamper:
        payload["To"] = "+15555550200"
    return client.post(path, data=payload, headers=headers)


class SignatureTests(unittest.TestCase):
    def test_valid_signature_returns_shop_greeting(self):
        with patch.dict(os.environ, ENV):
            response = post_signed(build(FakeDb()), INCOMING, incoming_form())
        self.assertEqual(response.status_code, 200)
        body = response.text
        # Ampersand must be escaped for TwiML to remain well-formed.
        self.assertIn("Griffin Muffler &amp; Brake Center", body)
        self.assertIn("Hi, I&#x27;m Rivit" if "&#x27;" in body else "Hi, I'm Rivit", body)
        self.assertEqual(response.headers["content-type"], "application/xml")

    def test_tampered_parameter_is_rejected(self):
        with patch.dict(os.environ, ENV):
            response = post_signed(build(FakeDb()), INCOMING, incoming_form(), tamper=True)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Rivit", response.text)

    def test_missing_signature_is_rejected(self):
        with patch.dict(os.environ, ENV):
            response = build(FakeDb()).post(INCOMING, data=incoming_form())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Rivit", response.text)

    def test_wrong_signing_key_is_rejected(self):
        with patch.dict(os.environ, ENV):
            response = post_signed(build(FakeDb()), INCOMING, incoming_form(), key="an-attacker-token")
        self.assertEqual(response.status_code, 403)

    def test_signature_bound_to_public_url(self):
        """A proxy that reports http://internal:8080 must not validate Twilio's https URL."""
        env = dict(ENV)
        env["TWILIO_PUBLIC_BASE_URL"] = ""
        with patch.dict(os.environ, env):
            form = incoming_form()
            signature = sign("https://api.example.test" + INCOMING, form)
            response = build(FakeDb()).post(INCOMING, data=form, headers={"X-Twilio-Signature": signature})
        self.assertEqual(response.status_code, 403)

    def test_fails_closed_without_signing_credentials(self):
        env = dict(ENV)
        env["TWILIO_AUTH_TOKEN"] = ""
        env["TWILIO_WEBHOOK_SHARED_KEY"] = ""
        with patch.dict(os.environ, env):
            response = build(FakeDb()).post(INCOMING, data=incoming_form(), headers={"X-Twilio-Signature": "x"})
        self.assertEqual(response.status_code, 503)

    def test_shared_key_sha256_mode_is_supported(self):
        env = dict(ENV)
        env["TWILIO_AUTH_TOKEN"] = ""
        env["TWILIO_WEBHOOK_SHARED_KEY"] = "shared-key-not-real"
        env["TWILIO_WEBHOOK_SIGNATURE_ALGORITHM"] = "sha256"
        form = incoming_form()
        material = BASE + INCOMING
        for name in sorted(form):
            material += name + form[name]
        signature = base64.b64encode(
            hmac.new(b"shared-key-not-real", material.encode(), hashlib.sha256).digest()
        ).decode()
        with patch.dict(os.environ, env):
            response = build(FakeDb()).post(INCOMING, data=form, headers={"X-Twilio-Signature": signature})
        self.assertEqual(response.status_code, 200)

    def test_secret_never_appears_in_any_response(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            client = build(db)
            bodies = [
                post_signed(client, INCOMING, incoming_form()).text,
                post_signed(client, STATUS, {"CallSid": "CA1", "CallStatus": "completed"}).text,
                client.get("/api/voice/health").text,
            ]
        for body in bodies:
            self.assertNotIn(AUTH_TOKEN, body)
            self.assertNotIn(BRIDGE_KEY, body)


class RoutingTests(unittest.TestCase):
    def test_unknown_dialed_number_is_never_answered_by_ai(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            response = post_signed(build(db), INCOMING, incoming_form(To="+15555559999"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Rivit", response.text)
        self.assertIn("<Hangup/>", response.text)
        self.assertEqual(db.voice_calls.docs[0]["outcome"], "unmapped_number")
        self.assertIsNone(db.voice_calls.docs[0]["tenant_id"])

    def test_hold_mode_takes_no_message_and_asserts_no_shop_facts(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            response = post_signed(build(db), INCOMING, incoming_form())
        body = response.text
        self.assertIn("still being tested", body)
        self.assertIn("<Hangup/>", body)
        for forbidden in ("<Connect>", "<Dial", "<Record", "open until", "$", "appointment"):
            self.assertNotIn(forbidden, body)
        self.assertEqual(db.voice_calls.docs[0]["mode"], "greeting_hold")

    def test_live_flag_without_secure_stream_falls_back_to_hold(self):
        env = dict(ENV)
        env["WRENCHRELAY_VOICE_LIVE_APPROVED"] = "true"
        env["WRENCHRELAY_VOICE_STREAM_URL"] = "http://insecure.example/media"
        db = FakeDb()
        with patch.dict(os.environ, env):
            response = post_signed(build(db), INCOMING, incoming_form())
        self.assertNotIn("<Connect>", response.text)
        self.assertEqual(db.voice_calls.docs[0]["mode"], "greeting_hold")

    def test_live_mode_streams_with_consent_disclosure(self):
        env = dict(ENV)
        env["WRENCHRELAY_VOICE_LIVE_APPROVED"] = "true"
        env["WRENCHRELAY_VOICE_STREAM_URL"] = "wss://api.example.test/api/voice/media"
        db = FakeDb()
        with patch.dict(os.environ, env):
            response = post_signed(build(db), INCOMING, incoming_form())
        body = response.text
        self.assertIn("<Connect><Stream", body)
        self.assertIn('url="wss://api.example.test/api/voice/media?call_sid=', body)
        self.assertIn("&amp;token=", body)
        self.assertNotIn(BRIDGE_KEY, body, "the media URL carries a per-call token, never the key")
        self.assertIn("may be recorded", body)
        self.assertIn('name="tenant_id" value="griffin-muffler"', body)
        self.assertEqual(db.voice_calls.docs[0]["mode"], "live")

    def test_live_flag_without_bridge_key_falls_back_to_hold(self):
        env = dict(ENV)
        env["WRENCHRELAY_VOICE_LIVE_APPROVED"] = "true"
        env["WRENCHRELAY_VOICE_STREAM_URL"] = "wss://api.example.test/api/voice/media"
        env["WRENCHRELAY_VOICE_BRIDGE_KEY"] = ""
        db = FakeDb()
        with patch.dict(os.environ, env):
            response = post_signed(build(db), INCOMING, incoming_form())
        self.assertNotIn("<Connect>", response.text)
        self.assertEqual(db.voice_calls.docs[0]["mode"], "greeting_hold")

    def test_inbound_disabled_returns_503_not_audio(self):
        env = dict(ENV)
        env["WRENCHRELAY_VOICE_INBOUND_ENABLED"] = "false"
        with patch.dict(os.environ, env):
            response = post_signed(build(FakeDb()), INCOMING, incoming_form())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Rivit", response.text)


class ReplayTests(unittest.TestCase):
    def test_duplicate_call_delivery_creates_one_call_record(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            client = build(db)
            first = post_signed(client, INCOMING, incoming_form())
            second = post_signed(client, INCOMING, incoming_form())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.text, first.text)
        self.assertEqual(len(db.voice_calls.docs), 1)

    def test_status_callback_is_idempotent_per_state(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            client = build(db)
            for _ in range(2):
                post_signed(client, STATUS, {"CallSid": "CA2", "CallStatus": "completed"})
            post_signed(client, STATUS, {"CallSid": "CA2", "CallStatus": "busy"})
        record = db.voice_calls.find_one({"call_sid": "CA2"})
        self.assertEqual(sorted(record["status_history"]), ["busy", "completed"])


class IntakeTests(unittest.TestCase):
    def post_intake(self, client, payload, key=BRIDGE_KEY):
        headers = {"X-Rivit-Bridge-Key": key} if key else {}
        return client.post(INTAKE, json=payload, headers=headers)

    def test_rejects_invented_shop_facts(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            response = self.post_intake(build(db), {
                "tenant_id": "griffin-muffler",
                "call_sid": "CA3",
                "fields": {"service_request": "brake noise", "price": "$149"},
            })
        self.assertEqual(response.status_code, 422)
        self.assertIn("may not assert shop facts", response.text)
        self.assertEqual(db.voice_intakes.docs, [])

    def test_rejects_unknown_fields_and_missing_bridge_key(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            client = build(db)
            self.assertEqual(self.post_intake(client, {"tenant_id": "griffin-muffler", "call_sid": "CA4",
                                                       "fields": {"service_request": "x"}}, key=None).status_code, 403)
            self.assertEqual(self.post_intake(client, {"tenant_id": "unknown", "call_sid": "CA4",
                                                       "fields": {"service_request": "x"}}).status_code, 403)
            self.assertEqual(self.post_intake(client, {"tenant_id": "griffin-muffler", "call_sid": "CA4",
                                                       "fields": {"service_request": "x", "mood": "angry"}}).status_code, 422)

    def test_saves_structured_intake_and_survives_reread(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            client = build(db)
            payload = {
                "tenant_id": "griffin-muffler",
                "call_sid": "CA5",
                "fields": {
                    "caller_name": "Test Caller",
                    "callback_number": "+15555550123",
                    "vehicle_year": "2016",
                    "vehicle_make": "Honda",
                    "vehicle_model": "Accord",
                    "service_request": "Grinding noise when braking",
                },
            }
            first = self.post_intake(client, payload)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["status"], "complete")
            self.assertEqual(first.json()["fields"]["vehicle_make"], "Honda")
            # Bridge retry must update in place, not duplicate the record.
            second = self.post_intake(client, payload)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(len(db.voice_intakes.docs), 1)
            # Operator sees it through the authenticated read endpoint.
            listed = client.get("/api/voice/intakes", params={"tenant_id": "griffin-muffler"})
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json()[0]["fields"]["caller_name"], "Test Caller")

    def test_operator_isolation_between_tenants(self):
        db = FakeDb()
        with patch.dict(os.environ, ENV):
            self.post_intake(build(db), {"tenant_id": "griffin-muffler", "call_sid": "CA6",
                                         "fields": {"service_request": "muffler leak"}})
            own = build(db, operator="owner@griffin.example")
            self.assertEqual(own.get("/api/voice/intakes", params={"tenant_id": "griffin-muffler"}).status_code, 200)
            other = build(db, operator="owner@second.example")
            self.assertEqual(other.get("/api/voice/intakes", params={"tenant_id": "griffin-muffler"}).status_code, 403)
            anonymous = build(db, authenticated=False)
            self.assertEqual(anonymous.get("/api/voice/intakes", params={"tenant_id": "griffin-muffler"}).status_code, 401)


class ConfigurationTests(unittest.TestCase):
    def test_tenant_config_refuses_inferred_shop_facts(self):
        bad = {"+15555550100": {"tenant_id": "t", "shop_name": "S", "greeting": "g", "prices": ["$99"]}}
        with self.assertRaises(ValueError):
            load_tenants(json.dumps(bad))

    def test_tenant_config_requires_e164_and_greeting(self):
        with self.assertRaises(ValueError):
            load_tenants(json.dumps({"5555550100": {"tenant_id": "t", "shop_name": "S", "greeting": "g"}}))
        with self.assertRaises(ValueError):
            load_tenants(json.dumps({"+15555550100": {"tenant_id": "t", "shop_name": "S"}}))
        with self.assertRaises(ValueError):
            load_tenants("{not json")

    def test_health_reports_readiness_without_secrets(self):
        with patch.dict(os.environ, ENV):
            payload = build(FakeDb()).get("/api/voice/health").json()
        self.assertTrue(payload["inbound_enabled"])
        self.assertFalse(payload["live_approved"])
        self.assertTrue(payload["signature_auth_configured"])
        self.assertEqual(payload["signature_algorithm"], "sha1")
        self.assertTrue(payload["tenants_valid"])
        self.assertEqual(payload["tenant_count"], 2)
        self.assertEqual(payload["max_call_seconds"], 600.0)

    def test_health_reports_the_effective_call_cap(self):
        with patch.dict(os.environ, dict(ENV, WRENCHRELAY_VOICE_MAX_CALL_SECONDS="90")):
            self.assertEqual(build(FakeDb()).get("/api/voice/health").json()["max_call_seconds"], 90.0)
        with patch.dict(os.environ, dict(ENV, WRENCHRELAY_VOICE_MAX_CALL_SECONDS="0")):
            self.assertEqual(build(FakeDb()).get("/api/voice/health").json()["max_call_seconds"], 600.0)


if __name__ == "__main__":
    unittest.main()
