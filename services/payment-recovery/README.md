# WrenchRelay payment recovery

This is an opt-in repair for the existing SQLite application, not the separate GitHub MongoDB implementation. No production startup setting or customer database is changed by committing these files.

## Confirmed production diagnosis

Read-only Stripe inspection found live WrenchRelay account `acct_1TxJj4CpTOQr6SYt`, existing active recurring prices and one enabled webhook endpoint `we_1U3OiTCpTOQr6SYtkPRCfw3F`. The endpoint uses `https://wrenchrelay-app-production.up.railway.app/api/billing/webhook`. Both this alias and `/api/stripe/webhook` currently return HTTP 503 with "Stripe webhook is not configured" to an unsigned request. A duplicate endpoint or URL change is not needed merely because OpenAPI lists one alias.

The live app advertises `stripe_enabled=false`. The last production boot diagnostic, October 24, reported no effective Stripe secret key or webhook secret. Railway and Vercel expose variable names but withhold their values through the connected access; those metadata entries do not prove either an empty value or a usable credential. No private values were printed or saved in this repair. Account charge capability remains unverified through the available Stripe operations.

## Recovery behavior

- Persist checkout identity before calling Stripe. Retries use the same provider idempotency key; old clients without a header reuse a pending account/price intent. Different tabs share the pending checkout even with different request keys. Existing nonterminal subscriptions block a second checkout until reconciled. Persisted Checkout Sessions are polled to recover a missed initial webhook; an ambiguous request beyond Stripe's idempotency window is held for review rather than creating another charge opportunity. Expired keys require a new intentional checkout instead of silently charging twice.
- Restrict checkout to server-configured recurring USD prices and an authenticated application account. Return URLs come only from the configured HTTPS origin. A successful return-page visit never grants access.
- Verify the raw webhook signature and timestamp before committing a minimal durable inbox record. Both existing webhook aliases use the same inbox. Acknowledgement follows persistence. Raw event bodies, card data and customer email are not stored by this layer.
- Process under a database-backed worker lease. An expired worker cannot commit after a successor. Fetch the current Stripe subscription instead of trusting notification order or granting access from invoice/checkout payloads.
- Reconcile known subscriptions every five minutes and terminal cancellations daily, including legacy subscriptions missed before this layer was installed. Queue transient failures with bounded exponential backoff and jitter; resume after process restarts. Unrelated products in the shared Stripe account are ignored. Unverifiable ownership goes to explicit review rather than granting access.
- Support cancellation followed by a new subscription without allowing a delayed old event to overwrite its successor. Active/trialing access requires an unexpired period and verification no older than 15 minutes. Other states deny access; no invented grace-period policy is applied.
- Keep the worker inside the existing app process, with a database lease across multiple processes. Billing failure does not stop unrelated maintenance routes. Monitor `/api/billing/health`, which reports only ready/unavailable without exposing account, queue or secret details.
- Preserve TLS hostname/certificate verification, restrict the Stripe origin and supported API paths, refuse redirects, bound response size, and retry POST only with an idempotency key. Read mounted secrets on each call so a correctly managed file rotation takes effect without process restart.

## Verify locally

Use an isolated environment; tests create disposable SQLite databases and fake Stripe responses. They never contact live Stripe or charge anyone.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-tests.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q recovery.py integration.py bootstrap.py
```

## Commission the repair in order

1. Obtain the exact running SQLite source archive and applied runtime patches. The production image reconstructs these at boot; it is not the repository's MongoDB Dockerfile. Preserve a consistent authorized SQLite backup and prove an isolated restore before installing new billing tables. Do not deploy the historical-source fixture as a substitute for live parity.
2. Review the live post-patch `backend/app.py`, its `current_user`, DB_PATH, users/billing_accounts/stripe_events schemas, and current webhook aliases. Match these to the adapter. This bootstrap requires `WR_PAYMENTS_HOST_SHA256`; an unreviewed source revision fails before integration. It does not independently authenticate a reviewer-supplied hash.
3. Copy this directory into the reviewed runtime image or source archive. Keep its files separate from `backend` imports. Retain the existing database path, volume, user IDs, auth/session keys and all unrelated startup behavior. Do not accept the existing unrelated staged Railway startup patch as a shortcut.
4. Supply a valid account-scoped live server key and the signing secret for **the existing** Stripe endpoint through the server's secret manager. Restrict API permissions to account/price/subscription reads and Checkout Session creation. Do not paste secrets into chat, source, logs or a public file. The available connected Stripe API operations do not provide server API-key creation/retrieval, so secure owner provisioning is a required one-time boundary. Do not rotate a valid hidden credential blindly.
5. Start with `WR_PAYMENTS_RECOVERY_ENABLED=false`. Review `.env.example`; confirm the selected default plan and display the actual price before enabling it. Existing inspected prices are Starter $39/month, Pro $49/month and Automotive Core $99/month. This repair changes no Stripe prices, no customer plan and no tax settings. Automotive overage metering is a separate contract and is not implemented by this recovery layer.
6. On an isolated restored candidate, set the reviewed source root/hash and enable the adapter. Start through `bootstrap.py`, for example `python /path/to/payment-recovery/bootstrap.py`, with `WR_PAYMENTS_HOST_ROOT` set to the exact canonical runtime root. The adapter adds its own tables to the **existing** database; it refuses an absent database. Configure process supervision and the host's existing dependency build. No new Railway service or paid plan is required.
7. Bind protected product operations to `Recovery.entitlement(authenticated_account_id)["active"]`, preserving the existing authorized trial and Brava lifetime rules through separately verified server-side checks. The adapter replaces billing status, checkout and webhook handlers; it does not silently rewrite every product authorization rule. Verify authenticated signup/login, pricing UI, checkout, renewal, cancellation, restoration, account deletion and paid-feature enforcement.
8. Execute the lifecycle and outage cases using an isolated Stripe sandbox with sandbox-only credentials/account/mode. Never switch the current live account into a fake test-mode claim. A staging sandbox configuration must use its own account/price IDs and explicit non-live settings; set STRIPE_LIVEMODE=false and STRIPE_SECRET_KEY_TEST in that isolated sandbox process. A database identity guard prevents reusing an initialized billing store for another Stripe account or mode. Fixture tests alone are not real Stripe commissioning evidence.
9. Keep the existing webhook destination and signing secret unless verification shows an actual mismatch. Stripe currently subscribes to checkout completion, subscription lifecycle and invoice events. The receiver can accept additional customer.subscription events; changing the Stripe endpoint's event set should be reviewed separately. Confirm authenticated deliveries commit and invalid signatures reject. Do not replay captured customer events into production as tests.
10. After acceptance and rollback evidence exist, enable the reviewed release on the existing production service. Verify payment health, authenticated checkout without completing a customer charge, actual webhook fulfillment and entitlement behavior. Retain the old image/config as rollback. Stop charging if ownership, entitlement or invoice reconciliation fails.

## Autonomy limits and operations

Ordinary network outages, duplicate/out-of-order notifications, missed webhooks, process restarts and mounted-key rotation recover automatically once deployed and correctly configured. Missing/revoked keys, account restrictions, wrong ownership, multiple conflicting subscriptions, disputed/refunded payments or broken DNS are not safely solved by inventing credentials or granting access. They remain visible failures requiring the appropriate owner action. Refund/dispute handling beyond the subscription's authoritative state is not included; do not market automatic dispute or financial reconciliation support.

The worker retries indefinitely for transient errors, with capped delay. Invalid bindings enter review. The payment-health route becomes unavailable for review/backlog/API failures; an external existing availability monitor must page the owner. No new notification destination or external message is created by this code. Enforce per-account rate limits at the existing authenticated API gateway; this library does not replace gateway admission control.

Completed/foreign inbox items are retained for 90 days and then removed. Retrying an older event is still safe because it fetches current subscription state rather than applying a financial mutation. Intent records and existing Stripe-event audit records need a reviewed retention policy; do not purge them blindly. Back up the same durable database volume and measure SQLite lock contention before expanding concurrency.

Payment health only establishes configured API reachability and queue processing, not a guarantee of future successful charges or business revenue. Live acceptance and recovery are not yet established. No production change, customer charge, new subscription, webhook replacement or credential rotation was performed while preparing this branch.
