"""Read-only, credential-safe Stripe live account / price preflight.

Intended to run only in the trusted, already configured backend environment.
No live checkout, charge, invoice, subscription, webhook or database mutation.
Never logs a key or a Stripe response body. Does not prove webhook delivery.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable

from recovery import BillingError, Settings, StripeAPI, secret_value


def run(expected_account: str, price_id: str, expected_amount_cents: int,
        api_factory: Callable[[Settings], StripeAPI] = StripeAPI) -> dict[str, object]:
    if os.getenv("STRIPE_LIVEMODE") != "true":
        raise BillingError("explicit_live_mode_required")
    key = secret_value("STRIPE_SECRET_KEY_LIVE")
    if not key.startswith(("sk_live_", "rk_live_")) or any(c in key for c in "\r\n"):
        raise BillingError("live_key_not_configured")
    if not isinstance(expected_amount_cents, int) or expected_amount_cents <= 0:
        raise BillingError("invalid_expected_amount")

    # Settings enforces account/price identifiers and HTTPS. StripeAPI.call
    # checks that GET /v1/account matches expected_account and charges_enabled
    # before it requests the price. These are GET-only Stripe operations.
    settings = Settings(expected_account, frozenset({price_id}), price_id,
                        "https://www.wrenchrelayllc.com", livemode=True)
    price = api_factory(settings).call("GET", "/v1/prices/" + price_id)
    recurring = price.get("recurring")
    if (price.get("id") != price_id or price.get("livemode") is not True
            or price.get("active") is not True
            or price.get("currency") != "usd"
            or price.get("unit_amount") != expected_amount_cents
            or price.get("type") != "recurring"
            or not isinstance(recurring, dict)
            or recurring.get("interval") != "month"
            or type(recurring.get("interval_count")) is not int
            or recurring["interval_count"] != 1):
        raise BillingError("live_price_mismatch")

    webhook_secret = secret_value("STRIPE_WEBHOOK_SECRET")
    webhook_format = webhook_secret.startswith("whsec_") and not any(
        c in webhook_secret for c in "\r\n")
    return {
        "result": "live_stripe_readonly_preflight_passed",
        "account_match": True,
        "active_monthly_price_match": True,
        "webhook_secret_format": webhook_format,
        "webhook_signature_verified": False,
        "signed_event_delivery_verified": False,
        "payment_to_entitlement_verified": False,
        "tax_registration_verified": False,
        "billing_commissioned": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--expected-price", required=True)
    parser.add_argument("--expected-amount-cents", required=True, type=int)
    args = parser.parse_args()
    try:
        result = run(args.expected_account, args.expected_price,
                     args.expected_amount_cents)
    except Exception as exc:
        # Do not print arbitrary exception messages (could include credentials,
        # provider responses, or network details).
        reason = str(exc) if isinstance(exc, BillingError) else "preflight_error"
        print(json.dumps({"result": "blocked", "reason": reason,
                          "billing_commissioned": False}), flush=True)
        return 1
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
