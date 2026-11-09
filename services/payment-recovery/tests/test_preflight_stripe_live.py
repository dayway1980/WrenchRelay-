"""No-network regression tests for read-only live Stripe account preflight."""
import os
import unittest
from unittest.mock import patch

from recovery import BillingError
from preflight_stripe_live import run


ACCOUNT = "acct_1TxJj4CpTOQr6SYt"
PRICE = "price_1UFHGCCpTOQr6SYtiVY9yE2R"


class FakeAPI:
    def __init__(self, settings, *, result=None):
        self.settings = settings
        self.result = result or {
            "id": PRICE, "livemode": True, "active": True,
            "currency": "usd", "unit_amount": 9900,
            "recurring": {"interval": "month"},
        }
        self.calls = []

    def call(self, method, path):
        self.calls.append((method, path))
        if method != "GET" or path != "/v1/prices/" + PRICE:
            raise AssertionError("unexpected operation")
        return self.result


class LivePreflightTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "STRIPE_LIVEMODE": "true",
            "STRIPE_SECRET_KEY_LIVE": "sk_live_dummy_not_for_network",
            "STRIPE_WEBHOOK_SECRET": "whsec_dummy_not_for_network",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_matches_live_account_and_exact_price_without_writes(self):
        clients = []
        def factory(settings):
            client = FakeAPI(settings)
            clients.append(client)
            return client
        result = run(ACCOUNT, PRICE, 9900, api_factory=factory)
        self.assertEqual([( "GET", "/v1/prices/" + PRICE)], clients[0].calls)
        self.assertEqual(clients[0].settings.account, ACCOUNT)
        self.assertTrue(result["account_match"])
        self.assertTrue(result["webhook_secret_format"])
        for field in ("webhook_signature_verified", "signed_event_delivery_verified",
                      "payment_to_entitlement_verified", "tax_registration_verified",
                      "billing_commissioned"):
            self.assertFalse(result[field])
        self.assertNotIn("sk_live", str(result))

    def test_wrong_mode_or_test_key_fails_closed(self):
        with patch.dict(os.environ, {"STRIPE_LIVEMODE": "false"}):
            with self.assertRaisesRegex(BillingError, "explicit_live_mode_required"):
                run(ACCOUNT, PRICE, 9900, api_factory=FakeAPI)
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY_LIVE": "sk_test_dummy"}):
            with self.assertRaisesRegex(BillingError, "live_key_not_configured"):
                run(ACCOUNT, PRICE, 9900, api_factory=FakeAPI)

    def test_incorrect_price_and_amount_fail_closed(self):
        with self.assertRaisesRegex(BillingError, "live_price_mismatch"):
            run(ACCOUNT, PRICE, 14900, api_factory=FakeAPI)
        with self.assertRaisesRegex(BillingError, "invalid_expected_amount"):
            run(ACCOUNT, PRICE, 0, api_factory=FakeAPI)
        with self.assertRaisesRegex(BillingError, "invalid_configuration"):
            run(ACCOUNT, "../price", 9900, api_factory=FakeAPI)

    def test_actual_transport_rejects_mismatched_account(self):
        # Exercise StripeAPI's real account-binding guard without network or keys.
        from unittest.mock import patch as mock_patch
        with mock_patch("recovery.StripeAPI._request", return_value={
            "id": "acct_AnotherUnrelatedAccount",
            "charges_enabled": True,
        }):
            with self.assertRaisesRegex(BillingError, "stripe_account_not_ready"):
                run(ACCOUNT, PRICE, 9900)

    def test_actual_transport_rejects_account_without_charge_capability(self):
        from unittest.mock import patch as mock_patch
        with mock_patch("recovery.StripeAPI._request", return_value={
            "id": ACCOUNT,
            "charges_enabled": False,
        }):
            with self.assertRaisesRegex(BillingError, "stripe_account_not_ready"):
                run(ACCOUNT, PRICE, 9900)

    def test_unverified_webhook_stays_unverified(self):
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            result = run(ACCOUNT, PRICE, 9900, api_factory=FakeAPI)
            self.assertFalse(result["webhook_secret_format"])
            self.assertFalse(result["signed_event_delivery_verified"])


if __name__ == "__main__":
    unittest.main()
