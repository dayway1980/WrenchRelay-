# WrenchRelay commissioning control — October 31, 2026

Status: NOT fully commissioned. This record supersedes assumptions, not historical evidence.

## Verified this pass

- Source inspected: 49f4117bf519dab14760c9961d71ef68322ed71b.
- Existing source inventory/syntax checks: 77 passed. These check source structure, not live business behavior.
- Android signing regression suite: 19 passed using disposable keys; no owner key used.
- Ten sampled public routes responded HTTP 200 at approximately 20:30 UTC. Signup/login return the same app shell; this does not prove registration or authentication.
- Production backend and gateway: online, one running replica each; no pending Railway work.
- Backend is SQLite 3.1.0-canonical-i18n. Repository README describes a different MongoDB runtime. Do not deploy that candidate over SQLite or use its green source checks as live acceptance evidence.
- Earlier verified deployment f0fbc7c6-a3bd-4e08-8aa8-c5bbafdaaaea has a webhook secret with the expected prefix. An unsigned request returned 400. Signed delivery remains unverified.
- Legacy Android builder deployment 2ed80666-3290-432b-b0a0-471cfe1fac0c failed: `/tmp/build.sh: line 347: gradle: command not found`. Startup also generated a keystore. No Play upload or certificate acceptance is proven.

## Read-only recheck — November 3, 2026

This section records read-only connected-account evidence gathered after PR #27 was published. Earlier October 31 checks above retain their original timestamp and scope.

- **GitHub:** PR #27 remains open, mergeable, and draft; not merged. Commit history in the remote branch is real, so the former "no remote push" statement at the end of this file has been corrected.
- **Railway:** The production SQLite backend and app gateway are online. The backend has one running replica and a persistent volume mounted at `/app/wr/data`. There are no staged production changes. The MongoDB service is sleeping; do not treat it as authoritative production data.
- **Stripe live-mode account:** One enabled webhook endpoint points to `https://wrenchrelay-app-production.up.railway.app/api/billing/webhook` and subscribes to checkout completion, invoice payment/failure and subscription lifecycle events. Active Stripe products exist. Endpoint enablement and product setup are *configuration evidence only*.
- **Gateway route:** The deployed gateway config rewrites `/api/billing/webhook` to `/api/stripe/webhook` before proxying to the backend/recovery targets. This needs an observed end-to-end Stripe delivery before marking the route PASS.
- **Gateway HTTP telemetry:** In the last 72 hours of the inspection, the endpoint registered three HTTP requests: two 5xx and one 4xx, with **zero recorded 2xx**. Historical gateway logs also include webhook POST responses of HTTP 503. The October 31 unsigned POST returned 400, which does not prove successful signature verification or fulfillment.
- **Stripe event history:** A read-only query of the available recent event history (up to 30 days) found no `checkout.session.completed`, `invoice.paid`, `customer.subscription.created`, `customer.subscription.updated`, or `invoice.payment_failed` events. This does not rule out older activity and does not prove that a particular endpoint can process valid events.
- **Runtime credential diagnostic:** The latest deploy startup logged that Stripe SDK, named credential variables, and webhook secret were present, with a `whsec_`-shaped webhook secret. Its `live_key_format` flag was false despite a populated live credential variable; this is an unresolved validation discrepancy, **not proof** that the credential is invalid. Do not print, copy into source control, or rotate credentials casually.
- **Privilege hygiene:** The failed legacy Android builder still lists Stripe secret-variable names. Review whether that builder needs them at all; remove only after checking dependencies and credentials separately. Do not transfer signing or payment secrets into build logs or artifacts.

**P0 release decision:** BILLING **UNVERIFIED**, not commissioned. No live charges, subscription mutations, or entitlement grants were made in this review. Do not switch on customer-facing paid access or deploy the MongoDB candidate on the strength of public GET checks.

**Next controlled acceptance test:** In an authorized Stripe sandbox, deliver a real Stripe-signed event to an isolated webhook implementation matching the canonical SQLite source; record delivery ID, timestamp, 2xx response, verified signature, durable idempotency record, correct account/price binding, and access changes. Replay the same event and prove no duplicate grant. Also test bad/stale/wrong-endpoint signatures and denied cross-tenant access. Before any live activation, reconcile the deployed source archive hash, confirm the deployed key belongs to the intended Stripe account, and perform an isolated SQLite backup restore.

## Ordered release gates

| Priority | Concrete work | Acceptance evidence | Customer outcome |
|---|---|---|---|
| P0 billing | Send a vendor-signed diagnostic event, then test subscription lifecycle in an isolated Stripe sandbox | Endpoint-specific delivery ID, 2xx, verified-signature log, durable event record, duplicate replay without repeated effects; reject invalid, stale and wrong-endpoint signatures | Payment and access agree |
| P0 billing | Validate deployed API credential and exact offer/price/customer binding; preserve fail-closed checkout guard | Intended Stripe account, expected currency/interval/price, unauthorized checkout denied, cross-user binding denied | Correct charge and correct account |
| P0 data | Identify authoritative SQLite file, encrypted backup destination, access owner and retention; restore a consistent SQLite backup into an isolated instance | Restore opens, integrity check passes, known records match; record restore duration and backup age | Customer records recoverable |
| P0 auth | Use two authorized disposable accounts in isolation | Signup/login/logout/reset, verified email for domain entitlements, Secure/HttpOnly cookies, cross-user record denial, deletion behavior | Private records stay private |
| P1 Android | Use existing default-branch unsigned-build and protected-signing workflow instead of the failing legacy builder | Exact Play package, unused versionCode and owner upload fingerprint; lint/unit/build/signature checks plus physical-device test | Installable update with stable identity |
| P1 technician | Run synthetic job through voice/text, interruption, noise fallback, evidence ranking and mandatory verification | Recorded user review; facts traceable; diagnosis unresolved until confirmed; missing/stale evidence causes abstention | Useful and trustworthy field workflow |
| P1 CMMS | Authorize least-privilege Fiix sandbox; keep read-only | Paging/rate-limit/wrong-asset/staleness tests and technician-approved imported records | Reliable existing-CMMS context |
| P1 commercial | Approve one pilot offer, scope, support, cancellation/refund terms and usage cost model | Signed pilot scope, actual measured service costs and support load; no invented ROI | Understandable purchase |
| P1 company | Reconcile entity/EIN, bank/Stripe ownership, ledger, tax obligations, contracts and data permissions with owner records | Owner-reviewed records; qualified legal/tax review where required | Accurate operations and obligations |
| P2 acquisition | Review truthful Industrial/Automotive claims and verify indexing | Search Console evidence and authorized pilot conversations; no fabricated customer metrics | Qualified prospects |

## Safe execution sequence

1. Preserve current source hashes, service config and persistent volume. No database replacement or key regeneration.
2. Finish signed-event verification through an authenticated Stripe Dashboard session. The prior browser-auth attempt timed out; no test-send success is claimed. Only live Stripe is connected; connect an authorized sandbox before simulating payment lifecycle.
3. Resolve source/runtime parity before modifying billing implementation. Recover the canonical SQLite source from the saved archive and compare with actual deployed archive hash.
4. Reuse the already reviewed GitHub Android workflow: it installs Gradle 8.11.1 and separates unsigned compilation from owner-key signing. Do not repair the legacy builder by generating another upload key. Retire redundant builders only after output and credential ownership are verified; no service has been stopped.
5. Add a regression for each confirmed code defect, run it in isolation, review the exact diff, deploy only that repair and verify the customer-facing behavior. Roll back on failed acceptance.
6. Keep every gate FAIL, PASS, BLOCKED or UNVERIFIED with timestamp, source and reviewer. HTTP 200, a secret prefix, a successful deployment, and source-text checks are insufficient to commission payments or the business.

## Reusable checks

`python scripts/commission_public.py` performs bounded GET-only checks, including JSON health, unauthenticated denial and nonexistent-route behavior. It never submits forms, charges, sends webhooks or grants entitlements. It deliberately reports billing_commissioned=false: billing requires separate acceptance evidence.

## Remaining owner/access dependencies

Authenticated Stripe test-send or authorized sandbox; canonical deployed-source parity; backup restore environment; two authorized QA accounts; Play Console identity and owner signing credentials; physical Android device; authorized Fiix sandbox; company financial/legal source records. Approval alone cannot supply these missing inputs.

## Executed public checker

At 2026-10-31 20:31:55 UTC (3:31:55 PM CDT), all eight checks passed: JSON SQLite health, unauthenticated work-order denial, nonexistent API route denial, home, Industrial, Automotive, privacy and terms. No authenticated workflow was exercised. Automatic review rejected including `/delete-account` because its no-mutation contract had not been verified; that route was removed from the reusable checker rather than bypassing review. No deletion was attempted in the revised run.

The checks and documentation were pushed to remote draft PR #27 on branch `audit/commissioning-20261031`; they have not been merged into `main`. No production deployment, signing, service shutdown, database migration or billing activation was performed by these PR changes.
