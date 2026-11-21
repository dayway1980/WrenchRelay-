# WrenchRelay customer-facing release gate — November 21, 2026

**Status: NOT COMMISSIONED. Do not deploy this branch or activate checkout until all gates below pass.**

## Changes in this branch
- Fail-closed checkout switch `WRENCHRELAY_BILLING_COMMISSIONED` (defaults false).
- `/api/config` advertises `billing_commissioned` based on live key, both plan prices, signing-secret presence and the explicit switch.
- New checkout attempts return 503 when billing is not commissioned; existing Stripe portal endpoint remains available.
- Free users who exhaust their AI request allowance see an upgrade explanation without losing typed notes; when billing is unavailable the UI requests contact instead of opening checkout.
- Correct the legal entity from the unrelated historical name to **WrenchRelay LLC**.

## What is actually deployed
Railway project `wrenchrelay`, production environment, routes through the `wrenchrelay-app` Caddy gateway to `wrenchrelay-production` (and recovery fallback). Those backends boot from sealed environment-stored archives and runtime patches, **not** directly from this GitHub main branch. The running server uses an SQLite volume; repo `server.py` uses MongoDB. Source parity is **not established**. Railway reports MongoDB service sleeping, separate from the running SQLite application.

**A GitHub merge or Vercel preview does not deliver these changes to the live backend.** Do not attach GitHub directly to the existing production service or replace its start command without restoring and reviewing the actual source and data first.

## Verified live Stripe account evidence
Use only WrenchRelay live account `acct_1TxJj4CpTOQr6SYt`. As checked Nov 21, 2026:
- Live subscriptions: zero.
- Tax registrations: zero.
- Multiple prices exist; some are Automotive subscriptions (including $99/mo and $149/mo), and others are different products. Never choose a price by amount alone.
- Previous webhook tests did not establish a completed Stripe-signed event, durable entitlement, and cancellation in the running application.
- A populated Stripe API key or an online Railway replica is not evidence of billing readiness.
- Do not collect Iowa sales tax before verifying an actual Department of Revenue registration; determine current service tax treatment separately.

## Mandatory commissioning steps
1. Obtain read-only hashes and inspect the **actual** runtime `backend/app.py`, release manifest, source archive and effective database path without exposing environment values.
2. Identify the live SQLite DB, produce a consistent backup, and independently test restoring to an isolated temporary instance.
3. Stage an identical backend copy and isolated database; validate login, free usage, and existing entitlements. Do not migrate live customers to the MongoDB repo implementation.
4. Set up a separate correctly connected Stripe **sandbox** and verify signed event delivery, idempotent durable persistence, exactly one entitlement, cancellation/refund/failure behavior, and negative/duplicate/out-of-order events. No real payment.
5. In a separate live, read-only check, verify that the actual backend secret key belongs to `acct_1TxJj4CpTOQr6SYt`, active live plan price IDs/amounts, and the webhook signing secret matches the configured endpoint.
6. Confirm Iowa/local tax registration and business sales-tax handling; verify Stripe Tax registration and automatic-tax decisions only if legally required. Do not create a tax registration in Stripe without actual agency registration.
7. Confirm user-visible price, period, trial, cancellation, refunds, privacy, consent and support pages; verify working email receipt and customer support.
8. Verify rollback (including database), security checks, private staging smoke tests, full authentication-to-checkout-to-entitlement and billing portal tests.
9. Only after passing every gate, explicitly authorize the deployment of a **reviewed matching runtime**. Switch `WRENCHRELAY_BILLING_COMMISSIONED=true` only on that reviewed runtime; validate externally.
10. Check customer-facing domains and authenticated flows again after deployment; monitor deployment and webhook logs for errors.

## Source smoke checks
`python -m unittest tests.test_billing_release_gate`

This smoke test is a **source-only** regression test. It does not prove a functioning checkout, login, payment, database, email or production release.

## Safety / rollback
Do not restart, redeploy, repoint DNS, edit secrets, connect a new source, merge or enable billing on the existing Railway gateway, production backend or recovery service until the source and data parity gates above are verified. Keep current services online for existing users.


## November 21 public-route check (read only)
- Railway marks `wrenchrelayllc.com` and `www.wrenchrelayllc.com` DNS propagated, ownership verified, and TLS certificate valid. In the prior 24 hours its Caddy gateway handled **137 HTTP 2xx** and **1,247 HTTP 4xx** requests with **no 5xx**. A sample of 4xx paths consisted largely of automated requests for unrelated WordPress/configuration files; no inference of customer failures is warranted from the aggregate.
- Logs include successful anonymous `GET /`, `GET /terms`, and `GET /privacy` on the WrenchRelay LLC domain. This proves a public landing page is serving responses, **not authenticated app flows**.
- Railway's `app.wrenchrelay.com` custom-domain record is **unverified**, still issuing a certificate, and reports that its required CNAME is absent; external DNS currently resolves through a different origin. The connected Cloudflare zone `wrenchrelay.com` appears `pending`, not confirmed authoritative for public routing. Do not alter DNS based solely on the stale Railway configuration.
- Vercel branch previews for the PR are `READY` with successful deployment checks, but are previews and do not commission the Railway backend or verify login/billing.
- A separate browser automation was blocked by the browser service's exhausted wallet. No new fee was authorized, and no live authenticated checkout test was completed.
