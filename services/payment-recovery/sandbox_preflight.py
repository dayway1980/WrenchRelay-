"""Read-only REAL Stripe sandbox and isolated app preflight.

No checkout, subscription mutation, webhook send, or real charge occurs.
This does not establish fulfillment; signed event and entitlement tests follow.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from recovery import BillingError, Settings, StripeAPI, secret_value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_origin(origin: str) -> str:
    parsed = urllib.parse.urlsplit(origin)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (parsed.scheme != "https" or parsed.netloc != host
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or host in ("localhost", "127.0.0.1", "wrenchrelayllc.com",
                        "www.wrenchrelayllc.com", "wrenchrelay.com", "www.wrenchrelay.com")
            or host == "wrenchrelay-app-production.up.railway.app"
            or "production" in host or host.endswith(".local")
            or "." not in host):
        raise BillingError("isolated_https_staging_origin_required")
    return origin.rstrip("/")


def load_settings(origin: str, account_id: str, price_id: str) -> Settings:
    if os.getenv("STRIPE_LIVEMODE") != "false":
        raise BillingError("explicit_sandbox_mode_required")
    key = secret_value("STRIPE_SECRET_KEY_TEST")
    if (not key.startswith(("sk_test_", "rk_test_")) or
            any(ch in key for ch in "\r\n")):
        raise BillingError("sandbox_key_not_configured")
    if not secret_value("STRIPE_WEBHOOK_SECRET").startswith("whsec_"):
        raise BillingError("sandbox_signing_secret_not_configured")
    return Settings(account_id, frozenset({price_id}), price_id,
                    validate_origin(origin), livemode=False)


def verify_price(api: StripeAPI, settings: Settings,
                 expected_amount_cents: int) -> None:
    # StripeAPI validates the test key and expected account against /v1/account.
    price = api.call("GET", "/v1/prices/" + settings.default_price)
    if (price.get("id") != settings.default_price or
            price.get("livemode") is not False or
            price.get("active") is not True or
            price.get("type") != "recurring" or
            price.get("currency") != "usd" or
            price.get("unit_amount") != expected_amount_cents or
            not isinstance(price.get("recurring"), dict) or
            price["recurring"].get("interval") != "month"):
        raise BillingError("sandbox_price_mismatch")


def inspect_staging(origin: str,
                    fetch: Callable[[str], tuple[int, dict]]) -> None:
    status, body = fetch(origin + "/api/billing/health")
    if status != 200 or body.get("status") != "ready":
        raise BillingError("staging_billing_health_unavailable")
    status, _ = fetch(origin + "/api/billing/status")
    if status != 401:
        raise BillingError("unauthenticated_billing_status_not_rejected")


def fetch_json(url: str) -> tuple[int, dict]:
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        response = opener.open(req, timeout=8)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        code = response.status
        raw = response.read(65537)
    if len(raw) > 65536:
        raise BillingError("staging_response_too_large")
    try:
        body = json.loads(raw)
    except (UnicodeError, ValueError):
        raise BillingError("staging_invalid_json") from None
    if not isinstance(body, dict):
        raise BillingError("staging_invalid_json")
    return code, body


def run(origin: str, account_id: str, price_id: str,
        expected_amount_cents: int,
        api_factory: Callable[[Settings], StripeAPI] = StripeAPI,
        fetch: Callable[[str], tuple[int, dict]] = fetch_json) -> dict:
    if not isinstance(expected_amount_cents, int) or expected_amount_cents <= 0:
        raise BillingError("invalid_expected_amount")
    settings = load_settings(origin, account_id, price_id)
    verify_price(api_factory(settings), settings, expected_amount_cents)
    inspect_staging(settings.origin, fetch)
    return {
        "result": "sandbox_preflight_passed",
        "mode": "test",
        "stripe_account_verified": True,
        "exact_monthly_price_verified": True,
        "isolated_staging_billing_health": "ready",
        "unauthenticated_billing_access": "denied",
        "real_signed_webhook_accepted": False,
        "payment_to_entitlement_verified": False,
        "billing_commissioned": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--staging-origin", required=True)
    p.add_argument("--sandbox-account", required=True)
    p.add_argument("--test-price", required=True)
    p.add_argument("--expected-amount-cents", required=True, type=int)
    args = p.parse_args()
    try:
        result = run(args.staging_origin, args.sandbox_account,
                     args.test_price, args.expected_amount_cents)
    except (BillingError, KeyError, OSError) as exc:
        detail = str(exc) if isinstance(exc, BillingError) else "preflight_error"
        print(json.dumps({"result": "blocked", "reason": detail,
                          "billing_commissioned": False}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
