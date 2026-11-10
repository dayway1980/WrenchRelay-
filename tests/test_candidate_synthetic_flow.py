"""Offline FastAPI smoke tests. All records and Stripe signatures are synthetic.

No real network, live card, Stripe API call, Railway service or Atlas database.
Uses mongomock for in-process persistence and FastAPI's local TestClient.
"""
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import mongomock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "api-service" / "main.py"

# Fail closed at import: never attach a live database or use real payment secrets.
for name in (
    "MONGO_URL", "MONGODB_URI", "STRIPE_SECRET_KEY",
    "STRIPE_SECRET_KEY_LIVE", "STRIPE_WEBHOOK_SECRET",
):
    os.environ.pop(name, None)
os.environ["JWT_SECRET"] = "local-only-unit-testing-key-not-for-production"
os.environ["DB_NAME"] = "synthetic_ci_only"

spec = importlib.util.spec_from_file_location("wrenchrelay_candidate_synthetic", SOURCE)
app_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app_module
spec.loader.exec_module(app_module)

TEST_WEBHOOK_SECRET = "whsec_local_only_no_real_stripe_account"
TEST_STRIPE_KEY = "sk_test_local_synthetic_do_not_use"


class CandidateSyntheticFlow(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient()["synthetic_ci_only"]
        self.original_db = app_module._db
        app_module._db = self.db
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        app_module._db = self.original_db

    def client(self):
        # Secure cookies should only travel over HTTPS.
        client = TestClient(app_module.app, base_url="https://testserver")
        self.clients.append(client)
        return client

    def register(self, client, email, name):
        result = client.post("/api/auth/register", json={
            "name": name,
            "email": email,
            "password": "Synthetic-Only-Passphrase-123!",
        })
        self.assertEqual(result.status_code, 200, result.text[:400])
        self.assertEqual(result.json()["email"], email)
        return result

    def test_registration_session_cookie_logout_and_expired_identity(self):
        client = self.client()
        result = self.register(client, "alice@synthetic.invalid", "Synthetic Alice")
        cookie = result.headers.get("set-cookie", "").lower()
        self.assertIn("wrenchrelay_session", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)

        profile = client.get("/api/me")
        self.assertEqual(profile.status_code, 200, profile.text[:300])
        self.assertEqual(profile.json()["email"], "alice@synthetic.invalid")

        self.assertEqual(client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(
            client.get("/api/me", headers={"Authorization": "Bearer fake.invalid.token"}).status_code,
            401,
        )

    def test_work_order_owner_isolation_and_anonymous_denial(self):
        alice, bob = self.client(), self.client()
        self.register(alice, "alice@synthetic.invalid", "Alice")
        self.register(bob, "bob@synthetic.invalid", "Bob")

        saved = alice.post("/api/work-orders", json={
            "mode": "industrial",
            "data": {"asset": "SYNTHETIC-MOTOR-001", "complaint": "Fictional bearing noise"},
            "narrative": "Synthetic test document; no real machine or customer.",
        })
        self.assertEqual(saved.status_code, 200, saved.text[:400])
        self.assertEqual(saved.json()["owner"], "alice@synthetic.invalid")
        self.assertEqual(len(alice.get("/api/work-orders").json()), 1)
        self.assertEqual(bob.get("/api/work-orders").status_code, 200)
        self.assertEqual(bob.get("/api/work-orders").json(), [])
        self.assertEqual(bob.get("/api/knowledge/search", params={"q": "SYNTHETIC"}).json(), [])
        self.assertEqual(self.client().get("/api/work-orders").status_code, 401)

    def test_unknown_billing_plan_is_rejected_without_stripe_request(self):
        alice = self.client()
        self.register(alice, "alice@synthetic.invalid", "Alice")
        response = alice.post("/api/billing/checkout", json={"plan": "not-a-real-plan"})
        self.assertEqual(response.status_code, 400)

    def test_bad_signature_is_rejected_and_valid_test_signature_is_accepted(self):
        alice = self.client()
        self.register(alice, "alice@synthetic.invalid", "Alice")
        body = json.dumps({
            "id": "evt_synthetic_signed_1",
            "type": "checkout.session.completed",
            "data": {"object": {
                "metadata": {"email": "alice@synthetic.invalid", "plan": "pro"},
                "client_reference_id": "alice@synthetic.invalid",
                "customer": "cus_synthetic",
                "subscription": "sub_synthetic",
            }},
        }, separators=(",", ":")).encode("utf-8")
        timestamp = int(time.time())
        bad_header = f"t={timestamp},v1={'0' * 64}"
        with patch.dict(os.environ, {
            "STRIPE_SECRET_KEY_LIVE": TEST_STRIPE_KEY,
            "STRIPE_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET,
        }):
            rejected = self.client().post(
                "/api/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": bad_header},
            )
            self.assertEqual(rejected.status_code, 400, rejected.text[:300])
            self.assertEqual(self.db.users.find_one({"email": "alice@synthetic.invalid"})["plan"], "free")

            message = f"{timestamp}.".encode("ascii") + body
            digest = hmac.new(
                TEST_WEBHOOK_SECRET.encode("utf-8"), message, hashlib.sha256
            ).hexdigest()
            accepted = self.client().post(
                "/api/billing/webhook", content=body,
                headers={"Content-Type": "application/json",
                         "Stripe-Signature": f"t={timestamp},v1={digest}"},
            )
            self.assertEqual(accepted.status_code, 200, accepted.text[:300])
            self.assertTrue(accepted.json()["received"])
            self.assertEqual(self.db.users.find_one({"email": "alice@synthetic.invalid"})["plan"], "pro")


if __name__ == "__main__":
    unittest.main()
