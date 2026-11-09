# Stripe live account binding and no-charge readiness — November 9, 2026

**Release gate: CLOSED.** This is a verified read-only Stripe/Railway inventory and a tool for a safe, later server-side check. It does **not** authorize a customer charge, production credential change, tax-registration claim, webhook replay or billing activation.

## Verified target

- Production Stripe account: `acct_1TxJj4CpTOQr6SYt` (name WrenchRelay).
- The live enabled `we_1U3OiTCpTOQr6SYtkPRCfw3F` webhook listens to `checkout.session.completed`, subscription lifecycle and invoice events, at `https://wrenchrelay-app-production.up.railway.app/api/billing/webhook`.
- Railway gateway `wrenchrelay-app` owns the above domain; its underlying backend is `wrenchrelay-production`. Variable **names** exist, but connected OAuth access redacts all values.
- Active Automotive Core **$99/month** recurring price: `price_1UFHGCCpTOQr6SYtiVY9yE2R` (lookup key `wrenchrelay_automotive_99_200_v1`). A separate **$149/month** Automotive Core price also exists. Do not silently select the wrong offer.
- Live Stripe API returns **zero PaymentIntents** and **zero subscriptions**; the listed Checkout Sessions are expired/unpaid. Two paid invoices have **zero amount due**, and are not paid customer revenue.
- Stripe Tax settings report `active`, but live Tax Registrations are empty. Do not infer tax collection is authorized or configured just because Stripe Tax is active.
- The second account ending `w0rSft` has Kind-er-Grid products, no WrenchRelay webhook and no checkout history; do not substitute its credentials.
- Production logs show earlier webhook POST responses including 503/500 and later 400. Bad-signature probes may correctly produce 400; they are **not evidence** of Stripe-signed event delivery or customer entitlement.
- A separate Stripe sandbox `acct_1TxJjZChyIdA3Bgu` has completed simulated payments and two **enabled** test webhook destinations pointing to separate Vercel receivers. This differs from the older sandbox note that called them disabled. They are not the verified Railway staging application; do not repoint them automatically.

## Step 1: Check the actual backend's live Stripe API key without disclosure

From a trusted Railway owner shell **inside the canonical backend**, after obtaining the exact reviewed script from this GitHub revision, install no new credential and set no new service-wide environment variable. Run:

```bash
cd /path/to/reviewed/services/payment-recovery
STRIPE_LIVEMODE=true python3 preflight_stripe_live.py \
  --expected-account acct_1TxJj4CpTOQr6SYt \
  --expected-price price_1UFHGCCpTOQr6SYtiVY9yE2R \
  --expected-amount-cents 9900
```

The process reads existing `STRIPE_SECRET_KEY_LIVE` via its environment or an existing mounted `_FILE` reference. It makes only Stripe `GET /v1/account` and `GET /v1/prices/{id}` requests with normal TLS verification, using the existing adapter's bounded retry logic. It fails closed if the actual key is not live, account mismatches, charges are disabled, or the price differs. **Do not** run this on a laptop without approved key access, and never print/copy any secret value.

A pass confirms server-side account and exact price identity **only**; the result explicitly says `billing_commissioned: false`. Webhook format is not webhook-signature verification. A failure should be investigated by the owner in the Stripe account's secure Dashboard/API keys view and Railway's secret manager. Do not guess a key, rotate a working secret blindly, or publish the key in logs.

If Railway SSH drops (as previously observed), this check remains **unexecuted**. GitHub tests with faked APIs do not substitute for a real backend execution.

## Step 2: End-to-end test gates

1. Establish exact post-patch backend source parity, durable SQLite backup and independently verified isolated restore (see `PRODUCTION_SOURCE_EVIDENCE_2026-11-09.md`).
2. Provision an isolated Stripe sandbox + isolated staging app/database and approved signing secret. Neither test event destinations nor a staging URL are independently established as a functioning WrenchRelay payment adapter today.
3. Use test-mode payments only; prove genuine signed event -> durable inbox -> correct authenticated paid entitlement, plus duplicate/out-of-order/retry and cancellation/failure behavior.
4. Separately verify the **live** endpoint signing secret belongs to the selected Stripe webhook and live key actually matches Qr6SYt. Validate price, tax, verified owner access, safe rollback and production release plan.
5. Do not collect Iowa sales tax until actual registration is established. Iowa explicitly treats telephone answering as taxable and provides free business permit registration through GovConnectIowa: https://revenue.iowa.gov/taxes/business-permit-registration . Stripe Tax registrations must represent a real tax-agency registration, not an assumed one.

## Operations change policy

No production environment, Stripe settings, customer charges, key, webhook URL, website, Railway deployment, customer database, tax registration or Play Store status is changed by this pull request. The key identity check is voluntary and read-only; Stripe account selection alone does not commission payments.
