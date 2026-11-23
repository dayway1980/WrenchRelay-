"""No-cost tests for the gated Realtime credential bridge.

All provider calls and databases are faked. Never use real OpenAI credentials.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from realtime_voice import MAX_SESSIONS_PER_USER_DAY, create_voice_router, realtime_enabled, validate_origin


class MemoryUsers:
    def __init__(self):
        self.count = 0
        self.email = "tech@example.test"

    def find_one_and_update(self, query, update):
        # Mirrors the per-account $exists / $lt atomic condition.
        if query["email"] != self.email or self.count >= MAX_SESSIONS_PER_USER_DAY:
            return None
        self.count += 1
        return {"email": self.email}

    def update_one(self, query, update):
        if self.count:
            self.count -= 1


class MemoryDb:
    def __init__(self):
        self.users = MemoryUsers()


def test_client(db, authenticated=True):
    app = FastAPI()

    def current_user():
        if not authenticated:
            raise HTTPException(status_code=401, detail="Sign in required")
        return db.users.email

    app.include_router(create_voice_router(
        current_user,
        lambda email: {"email": email, "active": True},
        lambda: db,
    ))
    return TestClient(app)


FLAGS = {
    "WRENCHRELAY_REALTIME_ENABLED": "true",
    "WRENCHRELAY_REALTIME_BUDGET_APPROVED": "true",
    "OPENAI_API_KEY": "sk-test-not-real",
    "JWT_SECRET": "test-only-salt",
}
PATH = "/api/realtime/client-secret"
ORIGIN = {"Origin": "https://wrenchrelayllc.com"}
INPUT = {"mode": "industrial", "language": "English"}


class RealtimeGateTests(unittest.TestCase):
    def test_off_by_default_even_with_api_key(self):
        with patch.dict(os.environ, {
            "WRENCHRELAY_REALTIME_ENABLED": "",
            "WRENCHRELAY_REALTIME_BUDGET_APPROVED": "",
            "OPENAI_API_KEY": "sk-test-not-real",
        }):
            self.assertFalse(realtime_enabled())
            r = test_client(MemoryDb()).post(PATH, json=INPUT, headers=ORIGIN)
            self.assertEqual(r.status_code, 503)

    def test_requires_authenticated_user(self):
        with patch.dict(os.environ, FLAGS):
            r = test_client(MemoryDb(), authenticated=False).post(PATH, json=INPUT, headers=ORIGIN)
            self.assertEqual(r.status_code, 401)

    def test_denies_cross_site_and_missing_origin(self):
        with patch.dict(os.environ, FLAGS):
            client = test_client(MemoryDb())
            self.assertEqual(client.post(PATH, json=INPUT, headers={"Origin": "https://attacker.example"}).status_code, 403)
            self.assertEqual(client.post(PATH, json=INPUT).status_code, 403)
            with self.assertRaises(HTTPException):
                validate_origin("https://attacker.example")

    def test_short_lived_secret_and_daily_limit(self):
        db = MemoryDb()
        fake = httpx.Response(200, json={"value": "ek_example_short_lived", "expires_at": 123456})
        with patch.dict(os.environ, FLAGS), patch("realtime_voice.httpx.post", return_value=fake) as upstream:
            client = test_client(db)
            first = client.post(PATH, json=INPUT, headers=ORIGIN)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["value"], "ek_example_short_lived")
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertEqual(first.json()["max_preview_seconds"], 180)
            self.assertNotIn("sk-test-not-real", first.text)
            sent = upstream.call_args.kwargs
            self.assertEqual(sent["json"]["expires_after"]["seconds"], 60)
            self.assertEqual(sent["json"]["session"]["type"], "realtime")
            self.assertEqual(sent["json"]["session"]["tool_choice"], "none")
            self.assertEqual(sent["json"]["session"]["tools"], [])
            self.assertEqual(sent["json"]["session"]["audio"]["input"]["transcription"]["model"], "gpt-transcribe")
            self.assertNotIn("example.test", sent["headers"]["OpenAI-Safety-Identifier"])
            self.assertEqual(len(sent["headers"]["OpenAI-Safety-Identifier"]), 64)
            self.assertEqual(client.post(PATH, json=INPUT, headers=ORIGIN).status_code, 200)
            self.assertEqual(client.post(PATH, json=INPUT, headers=ORIGIN).status_code, 429)
            self.assertEqual(upstream.call_count, 2)

    def test_upstream_error_refunds_token_and_hides_details(self):
        db = MemoryDb()
        fake = httpx.Response(401, json={"error": "PRIVATE KEY WRONG"}, request=httpx.Request("POST", "https://api.openai.com/v1/realtime/client_secrets"))
        with patch.dict(os.environ, FLAGS), patch("realtime_voice.httpx.post", return_value=fake):
            res = test_client(db).post(PATH, json=INPUT, headers=ORIGIN)
            self.assertEqual(res.status_code, 502)
            self.assertNotIn("PRIVATE KEY WRONG", res.text)
            self.assertEqual(db.users.count, 0)

    def test_request_constrains_mode_and_language(self):
        with patch.dict(os.environ, FLAGS):
            res = test_client(MemoryDb()).post(PATH, json={"mode": "any-other-app", "language": "invalid"}, headers=ORIGIN)
            self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
