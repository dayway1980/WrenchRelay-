"""Safety checks for the separate Rivit QA deployment overlay.

These tests use only in-memory FastAPI requests. No Twilio account, MongoDB,
OpenAI credentials, paid calls, or customer data is used.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api-service"))
from main import app  # noqa: E402

QA_TOKEN = "only-for-CI-mocked-qa-access-no-real-credential"
TEST_ENV = {
    "WR_ISOLATED_QA": "true",
    "WR_QA_ACCESS_TOKEN": QA_TOKEN,
    "WRENCHRELAY_VOICE_INBOUND_ENABLED": "false",
    "WRENCHRELAY_VOICE_LIVE_APPROVED": "false",
    "WRENCHRELAY_VOICE_STREAM_URL": "",
    "TWILIO_AUTH_TOKEN": "",
    "TWILIO_WEBHOOK_SHARED_KEY": "",
    "OPENAI_API_KEY": "",
    "STRIPE_SECRET_KEY": "",
    "STRIPE_SECRET_KEY_LIVE": "",
}


class RivitPrivateQABoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, TEST_ENV)
        self.env.start()
        self.client = TestClient(app, base_url="https://rivit-qa.example.test")

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_public_health_does_not_require_qa_key(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(QA_TOKEN, r.text)

    def test_private_qa_access_required_for_voice_health_and_config(self):
        for path in ("/api/voice/health", "/api/config", "/api/me"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(
                    self.client.get(path, headers={"X-WR-QA-Access": "wrong"}).status_code,
                    403,
                )

    def test_correct_qa_access_enables_readiness_but_not_billable_features(self):
        headers = {"X-WR-QA-Access": QA_TOKEN}
        voice = self.client.get("/api/voice/health", headers=headers)
        self.assertEqual(voice.status_code, 200)
        self.assertFalse(voice.json()["inbound_enabled"])
        self.assertFalse(voice.json()["live_approved"])
        # With no Mongo configured, /api/me can fail closed at its DB dependency
        # before reaching the session check; neither response grants identity.
        self.assertIn(self.client.get("/api/me", headers=headers).status_code, (401, 503))
        for path in ("/api/realtime/client-secret", "/api/ai/work-order",
                     "/api/billing/checkout", "/api/stripe/webhook"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, json={}, headers=headers).status_code, 503)

    def test_unsigned_inbound_closed_even_when_signing_key_is_configured(self):
        unsigned = self.client.post("/api/voice/incoming", data={"CallSid": "CA-invalid"})
        self.assertEqual(unsigned.status_code, 403)
        with patch.dict(os.environ, {
            "WRENCHRELAY_VOICE_INBOUND_ENABLED": "true",
            "TWILIO_AUTH_TOKEN": "ci-fake-no-real-twilio-key",
        }):
            unsigned = self.client.post("/api/voice/incoming", data={"CallSid": "CA-invalid"})
            self.assertEqual(unsigned.status_code, 403)
            # The same rule applies to callbacks.
            unsigned = self.client.post("/api/voice/status", data={"CallSid": "CA-invalid"})
            self.assertEqual(unsigned.status_code, 403)

    def test_no_qa_secret_fails_closed(self):
        with patch.dict(os.environ, {"WR_QA_ACCESS_TOKEN": ""}):
            r = self.client.get("/api/voice/health", headers={"X-WR-QA-Access": QA_TOKEN})
            self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
