"""Offline regression tests for the WrenchRelay Stripe lifecycle.

These tests use synthetic Stripe objects and an in-memory fake collection.
They never connect to Stripe or access production customer records.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-only-not-a-production-secret")
os.environ.pop("MONGO_URL", None)
os.environ.pop("MONGODB_URI", None)

import server


class FakeUsers:
    def __init__(self, record):
        self.record = dict(record)

    def find_one(self, query):
        return self.record if all(self.record.get(k) == v for k, v in query.items()) else None

    def update_one(self, query, update):
        if self.find_one(query):
            self.record.update(update["$set"])


def subscription(status="active", price="price_test_starter", sub_id="sub_test_1"):
    return {
        "id": sub_id,
        "customer": "cus_test_1",
        "status": status,
        "items": {"data": [{"price": {"id": price}}]},
    }


class BillingContractTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "STRIPE_PRICE_WRENCH_STARTER": "price_test_starter",
            "STRIPE_PRICE_WRENCH_PRO": "price_test_pro",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_db(self, **overrides):
        record = {
            "_id": "db_id_1",
            "email": "member@example.com",
            "plan": "free",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
        }
        record.update(overrides)
        return SimpleNamespace(users=FakeUsers(record))

    def test_recurring_price_controls_plan_not_untrusted_metadata(self):
        self.assertEqual(server._stripe_plan_from_subscription(subscription()), "starter")
        self.assertEqual(server._stripe_plan_from_subscription(subscription(price="price_test_pro")), "pro")
        self.assertIsNone(server._stripe_plan_from_subscription(subscription(price="price_unknown")))

    def test_active_payment_grants_confirmed_plan(self):
        db = self.make_db()
        result = server._sync_stripe_subscription(db, subscription(), expected_email="member@example.com")
        self.assertTrue(result)
        self.assertEqual(db.users.record["plan"], "starter")
        self.assertEqual(db.users.record["stripe_subscription_status"], "active")

    def test_subscription_cancel_and_failed_payment_downgrade(self):
        db = self.make_db(stripe_customer_id="cus_test_1", stripe_subscription_id="sub_test_1", plan="starter")
        self.assertTrue(server._sync_stripe_subscription(db, subscription(status="canceled")))
        self.assertEqual(db.users.record["plan"], "free")
        db.users.record["plan"] = "starter"
        self.assertTrue(server._sync_stripe_subscription(db, subscription(status="past_due")))
        self.assertEqual(db.users.record["plan"], "free")

    def test_unknown_price_never_grants_a_plan(self):
        db = self.make_db()
        self.assertFalse(server._sync_stripe_subscription(db, subscription(price="price_unknown"), expected_email="member@example.com"))
        self.assertEqual(db.users.record["plan"], "free")

    def test_account_customer_mismatch_fails_closed(self):
        db = self.make_db(stripe_customer_id="cus_another")
        self.assertFalse(server._sync_stripe_subscription(db, subscription(), expected_email="member@example.com"))
        self.assertEqual(db.users.record["plan"], "free")

    def test_stale_subscription_event_cannot_downgrade_replacement(self):
        db = self.make_db(
            stripe_customer_id="cus_test_1",
            stripe_subscription_id="sub_current",
            plan="pro",
        )
        self.assertFalse(server._sync_stripe_subscription(db, subscription(status="canceled", sub_id="sub_old")))
        self.assertEqual(db.users.record["plan"], "pro")

    def test_employer_lifetime_entitlement_is_preserved(self):
        db = self.make_db(email="worker@bravatile.com", plan="pro_lifetime")
        self.assertTrue(server._sync_stripe_subscription(db, subscription(status="canceled"), expected_email="worker@bravatile.com"))
        self.assertEqual(db.users.record["plan"], "pro_lifetime")

    def test_invoice_subscription_id_classic_and_modern(self):
        self.assertEqual(server._invoice_subscription_id({"subscription": "sub_old"}), "sub_old")
        self.assertEqual(server._invoice_subscription_id({
            "parent": {"subscription_details": {"subscription": "sub_new"}}
        }), "sub_new")
        self.assertIsNone(server._invoice_subscription_id({}))

    def test_checkout_preserves_customer_and_subscription_metadata(self):
        user = "member@example.com"
        with patch.object(server, "stripe_key", return_value="sk_test_fake"), \
             patch.object(server, "user_doc", return_value={"email": user, "plan": "free"}), \
             patch.object(server.stripe.checkout.Session, "create", return_value=SimpleNamespace(url="https://checkout.stripe.com/test")) as create:
            result = server.billing_checkout(server.CheckoutRequest(plan="starter"), None, user=user)
        self.assertEqual(result["url"], "https://checkout.stripe.com/test")
        self.assertEqual(create.call_args.kwargs["subscription_data"]["metadata"]["plan"], "starter")
        self.assertEqual(create.call_args.kwargs["mode"], "subscription")


class WebhookContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_signed_checkout_reconciles_subscription(self):
        event = {
            "type": "checkout.session.completed",
            "data": {"object": {
                "mode": "subscription", "subscription": "sub_test_1",
                "customer": "cus_test_1", "client_reference_id": "member@example.com",
                "metadata": {"email": "member@example.com", "plan": "starter"},
            }},
        }
        request = SimpleNamespace(body=AsyncMock(return_value=b'{"fake":true}'),
                                  headers={"stripe-signature": "test_signature"})
        fake_db = SimpleNamespace(users=FakeUsers({
            "_id": "db_id_1", "email": "member@example.com", "plan": "free",
            "stripe_customer_id": None, "stripe_subscription_id": None,
        }))
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_fake"}), \
             patch.object(server, "stripe_key", return_value="sk_test_fake"), \
             patch.object(server.stripe.Webhook, "construct_event", return_value=event), \
             patch.object(server.stripe.Subscription, "retrieve", return_value=subscription()), \
             patch.object(server, "require_db", return_value=fake_db):
            response = await server.billing_webhook(request)
        self.assertTrue(response["received"])
        self.assertEqual(fake_db.users.record["plan"], "starter")


if __name__ == "__main__":
    unittest.main()
