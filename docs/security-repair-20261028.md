# Security boundary repair — October 28, 2026

Scope: canonical repository server.py and Vercel api-service/main.py, matching dependency manifests, and security regression CI. These sources are not established as the currently running Railway archive.

## Changes

- Require a configured administrator email and a verified account for admin status. Missing admin configuration returns 503; other users return 403.
- Require JWT subject and expiration, reject deleted accounts, and compare the account's session epoch. Old tokens are revoked when ownership is first established through verified Google sign-in.
- Password registration no longer establishes email ownership or grants domain-based lifetime access. Existing unverified lifetime records are treated as free accounts. Verified Brava accounts retain the promised lifetime plan.
- On first Google verification, discard any password and sessions created before ownership was proven. Legacy accounts lacking the new verification flag must sign in with Google again to establish verification. An email-password verification/recovery workflow is not introduced here.
- Require an exact trusted Origin for unsafe requests carrying the session cookie. Bearer-only clients remain supported. Cookie-authenticated clients must send Origin. CORS configuration is the explicit cross-origin trust boundary.
- Grant a paid Starter/Pro plan only from a signed, paid subscription checkout event with customer and subscription identifiers. Support delayed-payment success events; reject arbitrary plan metadata. Existing signature timestamp validation remains in force. No live charge or webhook was sent.
- Upgrade both backend manifests together: FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1 with its resolver-selected core, Stripe 11.6.1 (same major as repo), h11 0.16.0, httptools 0.9.0, python-multipart 0.0.32 and certifi 2026.10.23. Other dependency versions remain unchanged.
- Add local TLS positive/negative checks, package PEM-content verification, API security tests, parser regressions and Python 3.11/3.13 CI.

## Validation and limits

The initial local security suite reproduced 20 failures before implementation. Validation uses an isolated Python 3.12 environment, fake in-memory database boundaries and locally signed synthetic events. Genuine Stripe Webhook signature verification is exercised; Google verification is stubbed at the external identity-provider boundary. No external payment service or production data is used.

The shipped Stripe PEM contains the 12 documented roots and excludes the three affected names identified by the vendor bulletin. Local OpenSSL context inspection additionally reported host trust material absent from that PEM. Package bytes alone therefore do not establish the final trust behavior of production. The local TLS test proves the actual SDK rejects an untrusted certificate and a mismatched hostname and accepts an explicitly trusted local test certificate; it is not a compromised-CA production probe.

Docker and Python 3.13 are unavailable locally. CI covers Python 3.11 and 3.13 when run. This branch does not change frontend code or perform a container build locally.

## Production boundary

Production Railway currently uses a separately archived source bootstrapped by its startup command, historically pins Stripe 16.0.0 and has a staged CA mitigation. Deploying this repository branch is not a verified repair of that archive. Do not overwrite the running production source or pending configuration as a shortcut.

Before release: map the active hostname/deployment/source, review migration effects on existing Brava/password accounts and Origin-bearing clients, confirm CI and image build, then use the approved deployment path. Confirm installed versions and serving-process CA configuration afterwards. Previously cancelled deployment approval must not be bypassed. Pending PR12 Bun/runtime updates remain a separate rollout.

Unmounted backend router variants, Supabase configuration, frontend dependency security, Android signing/Play release, complete subscription lifecycle/reconciliation, real MongoDB integration, rate limiting and production commissioning are not validated by this change. This is a targeted security repair, not a claim that every app is commissioned or vulnerability-free.
