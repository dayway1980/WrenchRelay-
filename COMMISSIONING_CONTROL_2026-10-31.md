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

Changes are isolated on local branch `audit/commissioning-20261031`. No remote push, deployment, signing, service shutdown, database migration or billing activation has been performed in this pass.
