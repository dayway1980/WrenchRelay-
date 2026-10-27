"""Durable Stripe recovery for the existing WrenchRelay SQLite account model.

No card data, email, raw event body or credentials are persisted here.
Production integration requires an existing database, HTTPS, server authentication
and verified Stripe account/price configuration. Never import a client tenant ID.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol


class BillingError(Exception):
    """Safe machine-readable error; never embed an upstream response/secret."""


class ReviewRequired(BillingError):
    pass


@dataclass(frozen=True)
class Settings:
    account: str
    prices: frozenset[str]
    default_price: str
    origin: str
    livemode: bool = True

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlsplit(self.origin)
        if (not re.fullmatch(r"acct_[A-Za-z0-9]+", self.account)
                or self.default_price not in self.prices
                or not self.prices
                or any(not re.fullmatch(r"price_[A-Za-z0-9]+", p) for p in self.prices)
                or parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/")):
            raise BillingError("invalid_configuration")


def secret_value(name: str) -> str:
    """Read a mounted secret on each call, allowing file-based rotation without restart."""
    path = os.getenv(name + "_FILE")
    if path:
        raw = Path(path).read_bytes()
        if len(raw) > 16384:
            raise BillingError("invalid_secret_file")
        return raw.decode().strip()
    return os.getenv(name, "").strip()


class API(Protocol):
    def call(self, method: str, path: str, parameters: Mapping[str, str] | None = None,
             idempotency: str | None = None) -> dict[str, Any]: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


class StripeAPI:
    """Bounded TLS-verified retries. POSTs require a persisted idempotency key."""
    def __init__(self, settings: Settings, key: Callable[[], str] | None = None):
        self.settings = settings
        self.key = key or (lambda: secret_value("STRIPE_SECRET_KEY_LIVE" if settings.livemode else "STRIPE_SECRET_KEY_TEST"))
        self.verified: tuple[str, float] | None = None

    def _request(self, method: str, path: str, parameters: Mapping[str, str] | None,
                 idempotency: str | None, key: str) -> dict[str, Any]:
        if method not in ("GET", "POST") or not re.fullmatch(
                r"/v1/(account|prices/price_[A-Za-z0-9]+|subscriptions/sub_[A-Za-z0-9]+|checkout/sessions(?:/cs_[A-Za-z0-9_]+)?)", path):
            raise BillingError("unsupported_stripe_operation")
        if method == "POST" and (path != "/v1/checkout/sessions" or not idempotency):
            raise BillingError("missing_idempotency")
        headers = {"Authorization": "Bearer " + key,
                   "Stripe-Version": "2026-06-24.dahlia",
                   "Content-Type": "application/x-www-form-urlencoded"}
        if idempotency:
            headers["Idempotency-Key"] = idempotency
        data = urllib.parse.urlencode(parameters or {}).encode() if method == "POST" else None
        # No certificate bypass and no redirect forwarding of the Authorization header.
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=os.getenv("STRIPE_CA_BUNDLE") or None)))
        for attempt in range(3):
            try:
                request = urllib.request.Request("https://api.stripe.com" + path,
                                                 data=data, headers=headers, method=method)
                with opener.open(request, timeout=8) as response:
                    raw = response.read(1048577)
                if len(raw) > 1048576:
                    raise BillingError("stripe_response_too_large")
                try:
                    obj = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    raise BillingError("invalid_stripe_response") from None
                if not isinstance(obj, dict):
                    raise BillingError("invalid_stripe_response")
                return obj
            except urllib.error.HTTPError as exc:
                retryable = exc.code in (409, 429) or exc.code >= 500
                if not retryable or attempt == 2:
                    raise BillingError("stripe_http_" + str(exc.code)) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise BillingError("stripe_network_unavailable") from None
            time.sleep(min(2 ** attempt, 4) + secrets.randbelow(250) / 1000)
        raise BillingError("stripe_unavailable")

    def call(self, method: str, path: str, parameters: Mapping[str, str] | None = None,
             idempotency: str | None = None) -> dict[str, Any]:
        key = self.key()
        prefix = ("sk_live_", "rk_live_") if self.settings.livemode else ("sk_test_", "rk_test_")
        if not key.startswith(prefix) or "\r" in key or "\n" in key:
            raise BillingError("stripe_key_not_configured")
        fingerprint = hashlib.sha256(key.encode()).hexdigest()
        if not self.verified or self.verified[0] != fingerprint or self.verified[1] < time.time():
            account = self._request("GET", "/v1/account", None, None, key)
            if account.get("id") != self.settings.account or account.get("charges_enabled") is not True:
                raise BillingError("stripe_account_not_ready")
            self.verified = (fingerprint, time.time() + 300)
        return self._request(method, path, parameters, idempotency, key)


SCHEMA = """
CREATE TABLE IF NOT EXISTS wr_payment_store_identity (
id INTEGER PRIMARY KEY CHECK(id=1), stripe_account TEXT NOT NULL, livemode INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS wr_payment_intents (
 id TEXT PRIMARY KEY, account_id TEXT NOT NULL, price_id TEXT NOT NULL,
 request_hash TEXT UNIQUE, session_id TEXT, session_url TEXT,
 created INTEGER NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending', next_poll INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS wr_intent_pending ON wr_payment_intents(account_id,price_id,expires);
CREATE TABLE IF NOT EXISTS wr_payment_inbox (
 id TEXT PRIMARY KEY, type TEXT NOT NULL, subscription_id TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 next_at INTEGER NOT NULL, received INTEGER NOT NULL, error TEXT
);
CREATE TABLE IF NOT EXISTS wr_payment_subscriptions (
 id TEXT PRIMARY KEY, account_id TEXT NOT NULL, customer_id TEXT NOT NULL,
 status TEXT NOT NULL, price_id TEXT NOT NULL, period_end INTEGER NOT NULL,
 verified_at INTEGER NOT NULL, next_reconcile INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS wr_payment_worker (
 id INTEGER PRIMARY KEY CHECK(id=1), token TEXT, until_at INTEGER NOT NULL DEFAULT 0,
 heartbeat INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO wr_payment_worker(id) VALUES(1);
"""


class Recovery:
    def __init__(self, path: Path, settings: Settings, api: API,
                 clock: Callable[[], float] = time.time):
        self.path, self.settings, self.api, self.clock = path.resolve(), settings, api, clock
        if not self.path.is_file():
            raise BillingError("existing_database_required")
        with self.connection() as db:
            # Require the live application's schema; never create a replacement customer DB.
            for table in ("users", "billing_accounts", "stripe_events"):
                db.execute('SELECT 1 FROM "' + table + '" LIMIT 1')
            db.executescript(SCHEMA)
            db.execute("INSERT OR IGNORE INTO wr_payment_store_identity VALUES(1,?,?)", (settings.account, int(settings.livemode)))
            identity = db.execute("SELECT stripe_account,livemode FROM wr_payment_store_identity WHERE id=1").fetchone()
            if identity[0] != settings.account or identity[1] != int(settings.livemode):
                raise BillingError("database_billing_identity_mismatch")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                             timeout=3, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    def checkout(self, account_id: str, price: str | None, client_key: str | None = None) -> dict[str, str]:
        now = int(self.clock())
        selected = price or self.settings.default_price
        if selected not in self.settings.prices:
            raise BillingError("unapproved_price")
        if client_key and not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", client_key):
            raise BillingError("invalid_idempotency_key")
        request_hash = hashlib.sha256((account_id + ":" + client_key).encode()).hexdigest() if client_key else None
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM users WHERE account_id=?", (account_id,)).fetchone():
                raise BillingError("unknown_account")
            if db.execute("SELECT 1 FROM wr_payment_subscriptions WHERE account_id=? AND status IN ('active','trialing') AND period_end>?", (account_id, now)).fetchone():
                raise BillingError("subscription_already_present")
            legacy = db.execute("SELECT status,current_period_end FROM billing_accounts WHERE account_id=?", (account_id,)).fetchone()
            if legacy and legacy["status"] not in ("canceled", "incomplete_expired"):
                # Reconcile an existing subscription before offering a second one, including unknown expiry formats.
                raise BillingError("existing_subscription_requires_reconciliation")
            prior = db.execute("SELECT * FROM wr_payment_intents WHERE request_hash=?", (request_hash,)).fetchone() if request_hash else None
            if not prior:
                prior = db.execute("SELECT * FROM wr_payment_intents WHERE account_id=? AND state IN ('pending','open','reconciling','review') ORDER BY created DESC LIMIT 1", (account_id,)).fetchone()
            if prior and prior["state"] in ("done", "expired"):
                raise BillingError("checkout_expired_new_key_required")
            if prior and (prior["account_id"] != account_id or prior["price_id"] != selected):
                raise BillingError("idempotency_conflict")
            if prior and (prior["expires"] <= now or prior["state"] in ("reconciling", "review")):
                # Stripe may prune keys after 24 hours; never reuse an expired local key.
                raise BillingError("checkout_expired_new_key_required")
            if prior:
                intent = dict(prior)
            else:
                intent = dict(id=secrets.token_hex(24), account_id=account_id, price_id=selected,
                              created=now, expires=now + 23 * 3600, session_url=None, session_id=None)
                db.execute("INSERT INTO wr_payment_intents(id,account_id,price_id,request_hash,created,expires) VALUES(?,?,?,?,?,?)",
                           (intent["id"], account_id, selected, request_hash, now, now + 23 * 3600))
            db.commit()
        if intent["session_url"]:
            return {"id": intent["session_id"], "url": intent["session_url"]}
        price_obj = self.api.call("GET", "/v1/prices/" + selected)
        if (price_obj.get("id") != selected or price_obj.get("active") is not True or price_obj.get("livemode") is not self.settings.livemode
                or price_obj.get("type") != "recurring" or price_obj.get("currency") != "usd"):
            raise BillingError("price_not_ready")
        parameters = {"mode": "subscription", "success_url": self.settings.origin.rstrip("/") + "/?checkout=success",
                      "cancel_url": self.settings.origin.rstrip("/") + "/?checkout=cancel",
                      "line_items[0][price]": selected, "line_items[0][quantity]": "1",
                      "client_reference_id": intent["id"]}
        for scope in ("metadata", "subscription_data[metadata]"):
            parameters[scope + "[wr_checkout_id]"] = intent["id"]
            parameters[scope + "[account_id]"] = account_id
        result = self.api.call("POST", "/v1/checkout/sessions", parameters, "wr-checkout-" + intent["id"])
        url = urllib.parse.urlsplit(str(result.get("url", "")))
        sid = result.get("id")
        expires = result.get("expires_at")
        if result.get("livemode") is not self.settings.livemode or not isinstance(expires, int) or isinstance(expires, bool) or expires <= now:
            raise BillingError("invalid_checkout_response")
        if url.scheme != "https" or url.hostname != "checkout.stripe.com" or url.username or url.password or url.port not in (None,443) or not isinstance(sid, str) or not sid.startswith("cs_"):
            raise BillingError("invalid_checkout_response")
        with self.connection() as db:
            db.execute("UPDATE wr_payment_intents SET session_id=?,session_url=?,expires=?,state='open',next_poll=? WHERE id=?",
                       (sid, result["url"], expires, now, intent["id"]))
        return {"id": sid, "url": result["url"]}

    def receive(self, raw: bytes, signature: str, signing_secrets: tuple[str, ...]) -> bool:
        if not signing_secrets or any(not x.startswith("whsec_") for x in signing_secrets):
            raise BillingError("webhook_secret_not_configured")
        if len(raw) > 262144 or len(signature) > 4096:
            raise BillingError("oversized_event")
        parts: dict[str, list[str]] = {}
        for part in signature.split(","):
            key, _, value = part.partition("=")
            parts.setdefault(key.strip(), []).append(value)
        try:
            timestamps = parts.get("t", [])
            if len(timestamps) != 1:
                raise ValueError()
            timestamp = int(timestamps[0])
        except ValueError:
            raise BillingError("invalid_signature") from None
        if abs(self.clock() - timestamp) > 300:
            raise BillingError("stale_signature")
        signed = str(timestamp).encode() + b"." + raw
        if not any(hmac.compare_digest(hmac.new(s.encode(), signed, hashlib.sha256).hexdigest(), v)
                   for s in signing_secrets for v in parts.get("v1", [])):
            raise BillingError("invalid_signature")
        try:
            event = json.loads(raw)
            eid, kind = event["id"], event["type"]
            if (not re.fullmatch(r"evt_[A-Za-z0-9]+", eid) or not isinstance(kind, str)
                    or event.get("livemode") is not self.settings.livemode
                    or event.get("account", self.settings.account) != self.settings.account):
                raise ValueError()
            obj = event["data"]["object"]
            if kind.startswith("customer.subscription."):
                sub = obj.get("id")
            elif kind.startswith("invoice."):
                sub = obj.get("subscription") or ((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription")
            elif kind == "checkout.session.completed":
                sub = obj.get("subscription")
            else:
                return False
            if not isinstance(sub, str) or not re.fullmatch(r"sub_[A-Za-z0-9]+", sub):
                raise ValueError()
        except (KeyError, TypeError, ValueError, AttributeError):
            raise BillingError("invalid_event") from None
        now = int(self.clock())
        with self.connection() as db:
            prior = db.execute("SELECT type,subscription_id FROM wr_payment_inbox WHERE id=?", (eid,)).fetchone()
            if prior:
                if prior["type"] != kind or prior["subscription_id"] != sub:
                    raise BillingError("event_identity_conflict")
                return False
            db.execute("INSERT OR IGNORE INTO wr_payment_inbox(id,type,subscription_id,next_at,received) VALUES(?,?,?,?,?)",
                       (eid, kind, sub, now, now))
        return True

    def _lease(self) -> str | None:
        token, now = secrets.token_hex(24), int(self.clock())
        with self.connection() as db:
            changed = db.execute("UPDATE wr_payment_worker SET token=?,until_at=?,heartbeat=? WHERE id=1 AND until_at<=?",
                                 (token, now + 120, now, now)).rowcount
        return token if changed else None

    def run_once(self, limit: int = 25) -> int:
        if not 1 <= limit <= 100:
            raise BillingError("invalid_batch_limit")
        token = self._lease()
        if not token:
            return 0
        processed = 0
        try:
            now = int(self.clock())
            self._recover_checkouts(token)
            with self.connection() as db:
                db.execute("DELETE FROM wr_payment_inbox WHERE state IN ('done','ignored') AND received<?", (now-90*86400,))
                # Recover missed notifications for known subscriptions only.
                rows = db.execute("SELECT id FROM wr_payment_subscriptions WHERE next_reconcile<=? ORDER BY next_reconcile LIMIT 100", (now,)).fetchall()
                for row in rows:
                    db.execute("INSERT OR IGNORE INTO wr_payment_inbox(id,type,subscription_id,next_at,received) VALUES(?,?,?,?,?)",
                               ("reconcile:" + row["id"] + ":" + str(now // 300), "reconcile", row["id"], now, now))
                legacy = db.execute("SELECT stripe_subscription_id FROM billing_accounts WHERE stripe_subscription_id IS NOT NULL AND stripe_subscription_id NOT IN (SELECT id FROM wr_payment_subscriptions) LIMIT 100").fetchall()
                for row in legacy:
                    sid = row[0]
                    if re.fullmatch(r"sub_[A-Za-z0-9]+", sid):
                        db.execute("INSERT OR IGNORE INTO wr_payment_inbox(id,type,subscription_id,next_at,received) VALUES(?,?,?,?,?)", ("legacy:"+sid+":"+str(now//300), "reconcile", sid, now, now))
                work = db.execute("SELECT * FROM wr_payment_inbox WHERE state='pending' AND next_at<=? ORDER BY received,id LIMIT ?", (now, limit)).fetchall()
            for event in work:
                try:
                    snapshot = self.api.call("GET", "/v1/subscriptions/" + event["subscription_id"])
                    self._apply(dict(event), snapshot, token)
                    processed += 1
                except BillingError as exc:
                    self._failed(event["id"], token, str(exc), isinstance(exc, ReviewRequired))
                except Exception:
                    self._failed(event["id"], token, "unexpected_processing_failure", False)
            return processed
        finally:
            with self.connection() as db:
                db.execute("UPDATE wr_payment_worker SET until_at=0 WHERE id=1 AND token=?", (token,))

    def _recover_checkouts(self, token: str) -> None:
        now = int(self.clock())
        with self.connection() as db:
            rows = db.execute("SELECT * FROM wr_payment_intents WHERE state IN ('pending','open') AND next_poll<=? ORDER BY created LIMIT 10", (now,)).fetchall()
        for row in rows:
            try:
                if not row["session_id"]:
                    # Reuse the durable identity when Stripe's first response was lost.
                    self.checkout(row["account_id"], row["price_id"])
                    with self.connection() as db:
                        db.execute("BEGIN IMMEDIATE")
                        self._assert_lease(db,token)
                        db.execute("UPDATE wr_payment_worker SET heartbeat=?,until_at=? WHERE id=1 AND token=?", (int(self.clock()),int(self.clock())+120,token))
                        db.commit()
                    continue
                obj = self.api.call("GET", "/v1/checkout/sessions/" + row["session_id"])
                if (obj.get("id") != row["session_id"] or obj.get("livemode") is not self.settings.livemode
                        or obj.get("client_reference_id") != row["id"]):
                    raise ReviewRequired("checkout_identity_conflict")
                status = obj.get("status")
                with self.connection() as db:
                    db.execute("BEGIN IMMEDIATE")
                    self._assert_lease(db, token)
                    if status == "complete":
                        sub = obj.get("subscription")
                        if not isinstance(sub, str) or not re.fullmatch(r"sub_[A-Za-z0-9]+", sub):
                            raise ReviewRequired("checkout_subscription_missing")
                        db.execute("INSERT OR IGNORE INTO wr_payment_inbox(id,type,subscription_id,next_at,received) VALUES(?,?,?,?,?)", ("checkout:"+row["id"], "reconcile", sub, now, now))
                        db.execute("UPDATE wr_payment_intents SET state='reconciling',next_poll=? WHERE id=?", (now+300,row["id"]))
                    elif status == "expired":
                        db.execute("UPDATE wr_payment_intents SET state='expired' WHERE id=?", (row["id"],))
                    elif status == "open":
                        db.execute("UPDATE wr_payment_intents SET next_poll=? WHERE id=?", (now+300,row["id"]))
                    else:
                        raise ReviewRequired("checkout_status_unknown")
                    db.execute("UPDATE wr_payment_worker SET heartbeat=?,until_at=? WHERE id=1 AND token=?", (now,now+120,token))
                    db.commit()
            except BillingError as exc:
                with self.connection() as db:
                    db.execute("BEGIN IMMEDIATE")
                    self._assert_lease(db,token)
                    review = isinstance(exc, ReviewRequired) or str(exc)=="checkout_expired_new_key_required"
                    db.execute("UPDATE wr_payment_intents SET state=CASE WHEN ? THEN 'review' ELSE state END,next_poll=? WHERE id=?", (review,now+300,row["id"]))
                    db.execute("UPDATE wr_payment_worker SET heartbeat=?,until_at=? WHERE id=1 AND token=?", (now,now+120,token))
                    db.commit()

    def _assert_lease(self, db: sqlite3.Connection, token: str) -> None:
        if not db.execute("SELECT 1 FROM wr_payment_worker WHERE id=1 AND token=? AND until_at>?", (token, int(self.clock()))).fetchone():
            raise BillingError("worker_lease_lost")

    def _apply(self, event: dict[str, Any], obj: dict[str, Any], token: str) -> None:
        now = int(self.clock())
        if (obj.get("id") != event["subscription_id"] or obj.get("livemode") is not self.settings.livemode
                or not re.fullmatch(r"cus_[A-Za-z0-9]+", str(obj.get("customer", "")))):
            raise ReviewRequired("invalid_subscription_identity")
        items = (obj.get("items") or {}).get("data") or []
        if len(items) != 1:
            raise ReviewRequired("subscription_items_require_review")
        price = (items[0].get("price") or {}).get("id")
        period = items[0].get("current_period_end", obj.get("current_period_end"))
        status = obj.get("status")
        if price not in self.settings.prices:
            # A shared Stripe account can send events for unrelated apps/products.
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                self._assert_lease(db, token)
                db.execute("UPDATE wr_payment_inbox SET state='ignored',error='foreign_price_ignored' WHERE id=?", (event["id"],))
                db.commit()
            return
        if not isinstance(period, int) or isinstance(period, bool) or period < 0 or not isinstance(status, str):
            raise ReviewRequired("subscription_contract_requires_review")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._assert_lease(db, token)
            known = db.execute("SELECT account_id,stripe_customer_id FROM billing_accounts WHERE stripe_subscription_id=?", (obj["id"],)).fetchone()
            tracked = db.execute("SELECT account_id,customer_id AS stripe_customer_id FROM wr_payment_subscriptions WHERE id=?", (obj["id"],)).fetchone()
            known = known or tracked
            metadata = obj.get("metadata") or {}
            intent = db.execute("SELECT account_id FROM wr_payment_intents WHERE id=?", (metadata.get("wr_checkout_id", ""),)).fetchone()
            account = known["account_id"] if known else intent["account_id"] if intent else None
            if not account or (metadata.get("account_id") and metadata["account_id"] != account):
                raise ReviewRequired("unknown_subscription_owner")
            if known and known["stripe_customer_id"] and known["stripe_customer_id"] != obj["customer"]:
                raise ReviewRequired("subscription_customer_conflict")
            if not db.execute("SELECT 1 FROM users WHERE account_id=?", (account,)).fetchone():
                raise ReviewRequired("deleted_subscription_owner")
            # This launch adapter intentionally supports one subscription per application account.
            other = db.execute("SELECT stripe_subscription_id,status FROM billing_accounts WHERE account_id=?", (account,)).fetchone()
            write_current = True
            if other and other[0] and other[0] != obj["id"]:
                if tracked:
                    write_current = False  # An old subscription cannot replace its successor.
                elif not intent or other[1] not in ("canceled", "incomplete_expired"):
                    raise ReviewRequired("multiple_subscriptions_require_review")
            db.execute("INSERT INTO wr_payment_subscriptions VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,price_id=excluded.price_id,period_end=excluded.period_end,verified_at=excluded.verified_at,next_reconcile=excluded.next_reconcile",
                       (obj["id"], account, obj["customer"], status, price, period, now, now + (86400 if status in ("canceled", "incomplete_expired") else 300)))
            if write_current:
                db.execute("INSERT INTO billing_accounts(account_id,stripe_customer_id,stripe_subscription_id,status,price_id,current_period_end,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET stripe_customer_id=excluded.stripe_customer_id,stripe_subscription_id=excluded.stripe_subscription_id,status=excluded.status,price_id=excluded.price_id,current_period_end=excluded.current_period_end,updated_at=excluded.updated_at",
                           (account, obj["customer"], obj["id"], status, price, str(period), str(now)))
            if intent:
                db.execute("UPDATE wr_payment_intents SET state='done' WHERE id=?", (metadata.get("wr_checkout_id"),))
            if event["id"].startswith("evt_"):
                db.execute("INSERT OR IGNORE INTO stripe_events VALUES(?,?,?)", (event["id"], event["type"], str(now)))
            db.execute("UPDATE wr_payment_inbox SET state='done',error=NULL WHERE id=?", (event["id"],))
            db.execute("UPDATE wr_payment_worker SET heartbeat=?,until_at=? WHERE id=1 AND token=?", (now, now + 120, token))
            db.commit()

    def _failed(self, eid: str, token: str, error: str, review: bool) -> None:
        now = int(self.clock())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._assert_lease(db, token)
            event = db.execute("SELECT attempts FROM wr_payment_inbox WHERE id=?", (eid,)).fetchone()
            attempts = event[0] + 1
            delay = min(3600, 15 * 2 ** min(attempts - 1, 8)) + secrets.randbelow(5)
            # Persist only our error codes, never arbitrary exception text.
            safe = error if re.fullmatch(r"[a-z0-9_]{1,80}", error) else "processing_failed"
            db.execute("UPDATE wr_payment_inbox SET state=?,attempts=?,next_at=?,error=? WHERE id=?",
                       ("review" if review else "pending", attempts, now + delay, safe, eid))
            db.execute("UPDATE wr_payment_worker SET heartbeat=?,until_at=? WHERE id=1 AND token=?", (now, now + 120, token))
            db.commit()

    def entitlement(self, account_id: str) -> dict[str, Any]:
        now = int(self.clock())
        with self.connection() as db:
            row = db.execute("SELECT s.* FROM wr_payment_subscriptions s JOIN billing_accounts b ON b.stripe_subscription_id=s.id AND b.account_id=s.account_id WHERE s.account_id=?", (account_id,)).fetchone()
        return {"active": bool(row and row["status"] in ("active", "trialing") and row["period_end"] > now
                               and row["verified_at"] >= now - 900),
                "status": row["status"] if row else "unverified", "price_id": row["price_id"] if row else None}

    def health(self) -> dict[str, Any]:
        with self.connection() as db:
            pending = db.execute("SELECT COUNT(*),MIN(received),MAX(attempts) FROM wr_payment_inbox WHERE state='pending'").fetchone()
            review = db.execute("SELECT COUNT(*) FROM wr_payment_inbox WHERE state='review'").fetchone()[0]
            review += db.execute("SELECT COUNT(*) FROM wr_payment_intents WHERE state='review'").fetchone()[0]
            heartbeat = db.execute("SELECT heartbeat FROM wr_payment_worker WHERE id=1").fetchone()[0]
        return {"pending": pending[0], "oldest_pending_seconds": max(0, int(self.clock()) - pending[1]) if pending[1] else 0,
                "max_attempts": pending[2] or 0, "review_required": review, "last_success_or_failure_at": heartbeat}
