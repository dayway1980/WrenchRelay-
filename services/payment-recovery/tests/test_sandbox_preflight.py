import os
import unittest
from unittest.mock import patch

from recovery import BillingError
from sandbox_preflight import run, validate_origin


class StubAPI:
    def __init__(self, settings, *, amount=9900, livemode=False):
        self.settings = settings
        self.calls = []
        self.price = {
            "id": settings.default_price,
            "active": True,
            "livemode": livemode,
            "type": "recurring",
            "currency": "usd",
            "unit_amount": amount,
            "recurring": {"interval": "month"},
        }

    def call(self, method, path, parameters=None, idempotency=None):
        self.calls.append((method, path))
        if method == "GET" and path == "/v1/prices/" + self.settings.default_price:
            return self.price
        raise AssertionError("unexpected outbound API call")


class SandboxPreflightTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "STRIPE_LIVEMODE": "false",
            "STRIPE_SECRET_KEY_TEST": "sk_test_fake_sandbox_preflight_only",
            "STRIPE_WEBHOOK_SECRET": "whsec_fake_sandbox_preflight_only",
        }
        self.origin = "https://isolated-staging.example.net"
        self.account = "acct_fixture"
        self.price = "price_fixture"

    def inspect(self, *, env=None, amount=9900, remote_amount=9900,
                remote_livemode=False, ready=True, status_http=401):
        seen = []

        def make_api(settings):
            api = StubAPI(settings, amount=remote_amount, livemode=remote_livemode)
            seen.append(api)
            return api

        def fake_fetch(url):
            seen.append(url)
            if url.endswith("/api/billing/health"):
                return (200, {"status": "ready"}) if ready else (404, {"detail": "Not Found"})
            if url.endswith("/api/billing/status"):
                return status_http, {"detail": "Authentication required"}
            raise AssertionError("unexpected request")

        with patch.dict(os.environ, self.env if env is None else env, clear=True):
            value = run(self.origin, self.account, self.price, amount,
                        api_factory=make_api, fetch=fake_fetch)
        return value, seen

    def test_read_only_preflight_succeeds_but_never_commissions(self):
        result, seen = self.inspect()
        self.assertEqual(result["result"], "sandbox_preflight_passed")
        self.assertFalse(result["billing_commissioned"])
        self.assertFalse(result["real_signed_webhook_accepted"])
        self.assertFalse(result["payment_to_entitlement_verified"])
        self.assertEqual(seen[0].calls, [("GET", "/v1/prices/price_fixture")])
        self.assertEqual(seen[1:], [
            self.origin + "/api/billing/health",
            self.origin + "/api/billing/status"])

    def test_rejects_production_and_insecure_origins(self):
        for host in ("http://isolated-staging.example.net",
                     "https://wrenchrelay-app-production.up.railway.app",
                     "https://www.wrenchrelayllc.com",
                     "https://localhost",
                     "https://my-production-staging.example.net",
                     "https://attacker:password@staging.example.net",
                     "https://staging.example.net/evil"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(BillingError, "staging_origin"):
                    validate_origin(host)

    def test_explicit_sandbox_mode_required(self):
        with self.assertRaisesRegex(BillingError, "explicit_sandbox_mode"):
            self.inspect(env={**self.env, "STRIPE_LIVEMODE": "true"})

    def test_live_secret_rejected(self):
        with self.assertRaisesRegex(BillingError, "sandbox_key"):
            self.inspect(env={**self.env, "STRIPE_SECRET_KEY_TEST": "sk_live_do_not_use"})

    def test_missing_signing_secret_rejected(self):
        with self.assertRaisesRegex(BillingError, "signing_secret"):
            self.inspect(env={**self.env, "STRIPE_WEBHOOK_SECRET": ""})

    def test_wrong_amount_rejected(self):
        with self.assertRaisesRegex(BillingError, "sandbox_price_mismatch"):
            self.inspect(remote_amount=12000)

    def test_wrong_mode_rejected(self):
        with self.assertRaisesRegex(BillingError, "sandbox_price_mismatch"):
            self.inspect(remote_livemode=True)

    def test_missing_billing_health_rejected(self):
        with self.assertRaisesRegex(BillingError, "staging_billing_health"):
            self.inspect(ready=False)

    def test_billing_status_must_deny_anonymous(self):
        with self.assertRaisesRegex(BillingError, "unauthenticated"):
            self.inspect(status_http=200)


if __name__ == "__main__":
    unittest.main()
