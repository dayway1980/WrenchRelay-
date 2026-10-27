import hashlib
import hmac
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from recovery import BillingError, Recovery, Settings, StripeAPI


class FakeStripe:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.checkout_by_key = {}
        self.subscription = None
        self.checkout_state="open"

    def call(self, method, path, parameters=None, idempotency=None):
        self.calls.append((method, path, parameters, idempotency))
        if self.fail:
            raise BillingError("stripe_network_unavailable")
        if path.startswith("/v1/prices/"):
            return {"id": "price_pro", "active": True, "livemode": True,
                    "type": "recurring", "currency": "usd"}
        if path.startswith("/v1/checkout/sessions/"):
            create = next(x for x in self.calls if x[0]=="POST" and x[1]=="/v1/checkout/sessions")
            return {"id":"cs_live_fixture","livemode":True,"client_reference_id":create[2]["client_reference_id"],"status":self.checkout_state,"subscription":"sub_fixture"}
        if path == "/v1/checkout/sessions":
            if idempotency not in self.checkout_by_key:
                self.checkout_by_key[idempotency] = {"id": "cs_live_fixture", "livemode":True, "expires_at":2000000000,
                                                     "url": "https://checkout.stripe.com/c/pay/fixture"}
            return self.checkout_by_key[idempotency]
        if path.startswith("/v1/subscriptions/"):
            return self.subscription.copy()
        raise AssertionError(path)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "fixture.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.executescript("""
            CREATE TABLE users(account_id TEXT PRIMARY KEY);
            INSERT INTO users VALUES('a'); INSERT INTO users VALUES('b');
            CREATE TABLE billing_accounts(account_id TEXT PRIMARY KEY,
                stripe_customer_id TEXT,stripe_subscription_id TEXT,status TEXT,
                price_id TEXT,current_period_end TEXT,updated_at TEXT NOT NULL);
            CREATE TABLE stripe_events(event_id TEXT PRIMARY KEY,event_type TEXT,processed_at TEXT);
            """)
        self.now = 1800000000
        self.api = FakeStripe()
        self.settings = Settings("acct_fixture", frozenset(["price_pro"]), "price_pro",
                                 "https://www.wrenchrelayllc.com")
        self.r = Recovery(self.path, self.settings, self.api, lambda: self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, eid="evt_fixture", sub="sub_fixture", kind="customer.subscription.updated", **kwargs):
        e = {"id": eid, "type": kind, "livemode": True,
             "data": {"object": {"id": sub}}}
        e.update(kwargs)
        raw = json.dumps(e).encode()
        sig = hmac.new(b"whsec_fixture", str(self.now).encode()+b"."+raw, hashlib.sha256).hexdigest()
        return raw, "t="+str(self.now)+",v1="+sig

    def receive(self, **kwargs):
        raw, signature = self.event(**kwargs)
        return self.r.receive(raw, signature, ("whsec_fixture",))

    def bind(self):
        self.r.checkout("a", None)
        with self.r.connection() as db:
            intent = db.execute("SELECT id FROM wr_payment_intents").fetchone()[0]
        self.api.subscription = {"id":"sub_fixture", "customer":"cus_fixture", "status":"active", "livemode":True,
            "metadata":{"account_id":"a","wr_checkout_id":intent},
            "items":{"data":[{"price":{"id":"price_pro"},"current_period_end":self.now+3600}]}}

    def test_requires_existing_customer_database(self):
        other = Path(self.tmp.name) / "absent.sqlite3"
        with self.assertRaisesRegex(BillingError, "existing_database_required"):
            Recovery(other, self.settings, self.api)
        self.assertFalse(other.exists())

    def test_checkout_retries_reuse_one_persisted_intent_and_provider_key(self):
        one = self.r.checkout("a", "price_pro", "request_key_12345678")
        two = self.r.checkout("a", "price_pro", "request_key_12345678")
        self.assertEqual(one, two)
        self.assertEqual(len(self.api.checkout_by_key), 1)

    def test_legacy_client_without_header_reuses_pending_session(self):
        self.r.checkout("a", None)
        self.r.checkout("a", None)
        self.assertEqual(len(self.api.checkout_by_key), 1)

    def test_checkout_outage_recovers_without_second_session(self):
        self.api.fail = True
        with self.assertRaises(BillingError):
            self.r.checkout("a", None, "request_key_12345678")
        self.api.fail = False
        self.r.checkout("a", None, "request_key_12345678")
        with self.r.connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wr_payment_intents").fetchone()[0], 1)

    def test_prices_and_account_scope_are_server_controlled(self):
        for account, price in [("a", "price_other"), ("unknown", "price_pro")]:
            with self.assertRaises(BillingError):
                self.r.checkout(account, price)
        self.assertEqual(len(self.api.calls), 0)

    def test_duplicate_and_modified_events(self):
        self.assertTrue(self.receive())
        self.assertFalse(self.receive())
        with self.assertRaisesRegex(BillingError, "event_identity_conflict"):
            self.receive(sub="sub_other")

    def test_signature_and_timestamp_fail_closed(self):
        raw, signature = self.event()
        for payload, sig in [(raw+b" ", signature), (raw, "t=0,v1=x"), (raw, "t=bad,v1=x")]:
            with self.assertRaises(BillingError):
                self.r.receive(payload, sig, ("whsec_fixture",))

    def test_mode_and_provider_account_rejected(self):
        for kwargs in [{"livemode":False},{"account":"acct_other"}]:
            with self.assertRaises(BillingError):
                self.receive(**kwargs)

    def test_receipt_persists_no_raw_event_or_card_or_email_data(self):
        self.receive(email="should-not-persist@example.test", secret="not-stored")
        self.assertNotIn(b"should-not-persist", self.path.read_bytes())
        with self.r.connection() as db:
            self.assertEqual(db.execute("SELECT state FROM wr_payment_inbox").fetchone()[0], "pending")

    def test_authoritative_subscription_grants_and_cancel_revokes(self):
        self.bind(); self.receive()
        self.assertEqual(self.r.run_once(), 1)
        self.assertTrue(self.r.entitlement("a")["active"])
        self.assertFalse(self.r.entitlement("b")["active"])
        self.api.subscription["status"] = "canceled"
        self.receive(eid="evt_cancel")
        self.r.run_once()
        self.assertFalse(self.r.entitlement("a")["active"])

    def test_old_notification_cannot_reinstate_canceled_current_subscription(self):
        self.bind(); self.api.subscription["status"] = "canceled"
        self.receive(eid="evt_old")
        self.r.run_once()
        self.assertFalse(self.r.entitlement("a")["active"])

    def test_temporary_outage_retries_after_restart(self):
        self.bind(); self.receive(); self.api.fail = True
        self.r.run_once()
        self.assertEqual(self.r.health()["pending"], 1)
        self.assertEqual(self.r.health()["max_attempts"], 1)
        self.api.fail = False; self.now += 30
        restarted = Recovery(self.path, self.settings, self.api, lambda: self.now)
        self.assertEqual(restarted.run_once(), 1)
        self.assertTrue(restarted.entitlement("a")["active"])

    def test_missed_webhook_recovered_by_periodic_reconciliation(self):
        self.bind(); self.receive(); self.r.run_once()
        self.api.subscription["status"] = "canceled"; self.now += 301
        self.r.run_once()
        self.assertFalse(self.r.entitlement("a")["active"])

    def test_expired_verification_denies_privileged_access(self):
        self.bind(); self.receive(); self.r.run_once(); self.now += 901
        self.assertFalse(self.r.entitlement("a")["active"])

    def test_unknown_subscription_does_not_claim_other_account(self):
        self.bind(); self.api.subscription["metadata"]["wr_checkout_id"] = "unknown"
        self.receive(); self.r.run_once()
        self.assertEqual(self.r.health()["review_required"], 1)
        self.assertFalse(self.r.entitlement("a")["active"])

    def test_wrong_customer_requires_review_without_overwrite(self):
        self.bind(); self.receive(); self.r.run_once()
        self.api.subscription["customer"] = "cus_other"; self.receive(eid="evt_wrong")
        self.r.run_once()
        self.assertEqual(self.r.health()["review_required"], 1)
        with self.r.connection() as db:
            self.assertEqual(db.execute("SELECT stripe_customer_id FROM billing_accounts").fetchone()[0],"cus_fixture")

    def test_worker_lease_prevents_second_worker_and_expiry_blocks_commit(self):
        self.bind(); self.receive(); token = self.r._lease()
        self.assertEqual(self.r.run_once(), 0)
        self.now += 121
        with self.assertRaisesRegex(BillingError, "worker_lease_lost"):
            self.r._apply({"id":"evt_fixture","type":"customer.subscription.updated","subscription_id":"sub_fixture"}, self.api.subscription, token)
        self.assertEqual(self.r.run_once(), 1)

    def test_existing_subscriptions_reconcile_without_new_checkout(self):
        self.bind()
        with self.r.connection() as db:
            db.execute("INSERT INTO billing_accounts VALUES(?,?,?,?,?,?,?)",("a","cus_fixture","sub_fixture","active","price_pro",str(self.now+1000),str(self.now)))
            db.execute("DELETE FROM wr_payment_intents")
        self.api.subscription["metadata"] = {}
        self.r.run_once()
        self.assertTrue(self.r.entitlement("a")["active"])
        with self.assertRaises(BillingError):
            self.r.checkout("a", None)

    def test_no_live_key_means_no_stripe_request(self):
        api=StripeAPI(self.settings,key=lambda:"")
        with self.assertRaisesRegex(BillingError,"stripe_key_not_configured"):
            api.call("GET","/v1/prices/price_pro")


if __name__ == "__main__":
    unittest.main()

class RecoveryEdgeTests(unittest.TestCase):
    setUp = Tests.setUp
    tearDown = Tests.tearDown
    event = Tests.event
    receive = Tests.receive
    bind = Tests.bind

    def test_unrelated_app_price_is_ignored_without_entitlement(self):
        self.bind(); self.api.subscription['items']['data'][0]['price']['id']='price_signal'
        self.receive(); self.r.run_once()
        self.assertEqual(self.r.health()['review_required'],0)
        self.assertFalse(self.r.entitlement('a')['active'])
        with self.r.connection() as db:
            self.assertEqual(db.execute('SELECT state FROM wr_payment_inbox').fetchone()[0],'ignored')

    def test_rejoin_after_cancellation_and_late_old_event_preserves_new_subscription(self):
        self.bind(); self.receive(); self.r.run_once()
        old=dict(self.api.subscription)
        self.api.subscription['status']='canceled';self.receive(eid='evt_cancel');self.r.run_once()
        self.now+=24*3600
        self.r.checkout('a',None,'new_request_12345678')
        with self.r.connection() as db:
            intent=db.execute('SELECT id FROM wr_payment_intents ORDER BY created DESC LIMIT 1').fetchone()[0]
        self.api.subscription={**self.api.subscription,'id':'sub_new','status':'active','metadata':{'account_id':'a','wr_checkout_id':intent},'items':{'data':[{'price':{'id':'price_pro'},'current_period_end':self.now+3600}]}}
        self.receive(eid='evt_new',sub='sub_new');self.r.run_once()
        self.assertTrue(self.r.entitlement('a')['active'])
        self.api.subscription={**old,'status':'canceled'}
        self.receive(eid='evt_late',sub='sub_fixture');self.r.run_once()
        with self.r.connection() as db:
            self.assertEqual(db.execute('SELECT stripe_subscription_id FROM billing_accounts').fetchone()[0],'sub_new')
        self.assertTrue(self.r.entitlement('a')['active'])


class MissedCheckoutTests(unittest.TestCase):
    setUp=Tests.setUp
    tearDown=Tests.tearDown
    event=Tests.event
    receive=Tests.receive
    bind=Tests.bind

    def test_parallel_tabs_with_different_keys_reuse_pending_checkout(self):
        self.r.checkout('a',None,'request_tab_one_12345')
        self.r.checkout('a',None,'request_tab_two_12345')
        self.assertEqual(len(self.api.checkout_by_key),1)

    def test_completed_checkout_reconciles_without_any_webhook(self):
        self.bind();self.api.checkout_state='complete'
        self.r.run_once()
        self.assertTrue(self.r.entitlement('a')['active'])

    def test_unknown_checkout_timeout_stays_blocked_after_provider_key_window(self):
        self.api.fail=True
        with self.assertRaises(BillingError):self.r.checkout('a',None)
        self.now+=24*3600
        with self.assertRaisesRegex(BillingError,'checkout_expired_new_key_required'):
            self.r.checkout('a',None,'new_request_key_12345')
        self.assertEqual(len(self.api.checkout_by_key),0)

    def test_same_database_cannot_switch_to_another_stripe_account_or_mode(self):
        for settings in [Settings('acct_other',frozenset(['price_pro']),'price_pro','https://www.wrenchrelayllc.com'),Settings('acct_fixture',frozenset(['price_pro']),'price_pro','https://www.wrenchrelayllc.com',False)]:
            with self.assertRaisesRegex(BillingError,'database_billing_identity_mismatch'):
                Recovery(self.path,settings,self.api)
