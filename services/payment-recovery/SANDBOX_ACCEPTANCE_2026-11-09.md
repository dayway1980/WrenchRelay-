# WrenchRelay isolated Stripe sandbox acceptance — November 9, 2026

**Do not mistake these gates for production commissioning.** This plan is for a separately authenticated Stripe *sandbox* and an isolated copy of the actual SQLite application, never the production URL or production volume.

## Evidence available now

- Read-only Stripe sandbox inspection: account `acct_1TxJjZChyIdA3Bgu`, one active **$99/month** recurring test price `price_1UZYkxChyIdA3BgufdqmRzTl`, two historical successful simulated Checkout payments, and one trialing test subscription.
- As rechecked November 9, both existing sandbox webhook endpoints are **enabled**, but they target separate Vercel receiver URLs, not a reviewed `payment-recovery` staging instance. Enabled is not proof of a valid Stripe-signed payment-to-entitlement path. Do not blindly redirect them.
- Existing live FastAPI SQLite application responds with `stripe_enabled=true`, while `/api/billing/health` is HTTP 404. This does **not** indicate the new recovery adapter is installed or that payments are commissioned.
- Production `/tmp/wr-canonical.tgz` has the archive hash recorded in `PRODUCTION_SOURCE_EVIDENCE_2026-11-09.md`; post-patch `backend/app.py` and the restored DB remain unverified.
- The synthetic suite runs across three FastAPI/Starlette versions and is not a live Stripe webhook test.

## Gate A: Source parity and recovery (not yet passed)

1. Obtain the exact runtime `backend/app.py` fingerprint and review of relevant host authentication, route and DB schema contracts; do not assume the historical archive alone equals the running patched source.
2. Create a consistent, private encrypted backup of the canonical SQLite database and **restore it into a separate isolated environment**, checking integrity and expected schema/record counts without printing customer data.
3. Use a separate staging database and user credentials. Do not mount the production volume to the test service or reuse live auth/session keys.
4. Bind server-side protected product routes to the verified entitlement result. The payment-recovery adapter does not silently rewrite every legacy feature-permission check.

## Gate B: Isolated sandbox preflight (can be run after Gate A)

Provision secrets to the staging service's private secret manager, not chat, source code, terminal history, logs or publicly readable runtime settings. Minimum values include `STRIPE_LIVEMODE=false`, `STRIPE_SECRET_KEY_TEST`, the signing secret for the **correct new staging webhook endpoint**, `STRIPE_ACCOUNT_ID` and a reviewed test price. Do **not** reuse the live endpoint's webhook secret or test credentials.

Set the environment safely and execute (script reads test-mode values from protected environment variables or secret files; nothing is printed):

```bash
python sandbox_preflight.py \
  --staging-origin https://YOUR-ISOLATED-STAGING-HOST \
  --sandbox-account acct_1TxJjZChyIdA3Bgu \
  --test-price price_1UZYkxChyIdA3BgufdqmRzTl \
  --expected-amount-cents 9900
```

This **read-only** command checks Stripe test account authorization through `/v1/account`, the exact active test-mode monthly USD price, staging billing health returning `ready`, and anonymous billing status returning HTTP 401. It refuses live keys, live mode, known production origins, missing signing secret, wrong prices and unavailable staging health. It never creates sessions, subscriptions, events, charges or entitlements.

Passing preflight means only account/price/health/basic-auth-boundary acceptance: its JSON explicitly reports `real_signed_webhook_accepted=false`, `payment_to_entitlement_verified=false`, and `billing_commissioned=false`.

## Gate C: Real sandbox lifecycle (not yet passed)

With a separately reviewed enabled webhook destination under the sandbox account, perform an authorized **test-mode** monthly Checkout through the *isolated* staging application for a disposable, known user. Complete checkout only with Stripe test payment credentials. Verify:

- A genuine Stripe-signed `checkout.session.completed` or subscription event arrives at the configured staging endpoint and returns HTTP 2xx **after** durable inbox insertion; record Stripe event and delivery IDs in private evidence, without raw payloads or credentials.
- Re-deliver the exact same event and verify no duplicate inbox row, charge, subscription or entitlement.
- Delayed and out-of-order events reconcile against the current Stripe subscription; unpaid or mismatched customer/price, and other tenants' events, cannot grant access.
- A verified active subscription opens only that authenticated user's paid features; a mere redirect/callback or manually modified client plan does not grant access.
- Test invoice renewal, payment failure, cancellation at period end, immediate cancellation and recovery from an endpoint outage using test subscriptions; demonstrate correct access and rejection behavior.
- Verify missing/invalid signing secrets fail closed; prove unauthorized billing status remains HTTP 401, and unrelated routes remain healthy.
- Record the final accepted source hash, Stripe account, test price, deployment ID, isolated DB restore result, API responses, and reversible rollback procedure.

**Only then** may production staging and approved deployment be considered. Production activation additionally needs verification of the **live** Stripe account's server key/account identity, actual endpoint-specific signing secret, intended price, tax treatment, and webhook receipts before paid access is made customer-facing. Do not replay sandbox events into production.

## Safety and scope

This acceptance workflow creates no paid plan, production key, production webhook, production database mutation or external user charge automatically. The existing sandbox test subscription is test data, not evidence of the new WrenchRelay adapter's integration.
