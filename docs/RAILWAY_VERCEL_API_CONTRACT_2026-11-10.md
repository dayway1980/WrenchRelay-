# WrenchRelay API contract comparison — 10 November 2026

## Evidence and provenance

**Live canonical app:** the existing Railway Caddy public gateway at `wrenchrelay-app-production.up.railway.app` routes to `wrenchrelay-production.railway.internal:8080` (with recovery fallback). The exact read-only Vercel preview rewrite `/__bridge/railway-openapi` fetched canonical `/openapi.json` and returned HTTP 200, OpenAPI 3.1.0, `info.version=3.1.0-canonical-i18n`.

**Candidate app:** GitHub `dayway1980/WrenchRelay-` `api-service/main.py`, which Vercel deploys separately. Its route decorators were enumerated from source. At both candidate preview deployments, `/api/health/ready` returned HTTP 503 `database: not_configured`, and `/api/me` and `/api/work-orders` returned HTTP 503 `Authentication is not configured`. The bridge health returned HTTP 200 with `database=sqlite`, but that says **nothing** about readiness of the candidate API.

The source candidate advertises `APP_VERSION=2.0.0`. The Railway runtime is the **separate** 3.1.0 SQLite-backed service, not a deployment of this MongoDB-backed candidate.

## Route inventories

| Comparison | Distinct method + path |
|---|---:|
| Railway canonical (including public legal pages) | 26 |
| Vercel candidate FastAPI | 19 |
| Identical method + path | **6** |
| Canonical only | **20** |
| Candidate only | **13** |

### Shared exact method and path
- `GET /api/config`
- `GET /api/health`
- `GET /api/me`
- `GET /api/work-orders`
- `POST /api/auth/login`
- `POST /api/auth/register`

**Shared path does not imply matching request/response, cookies, permissions or data model.**

### Critical breaking differences

| Workflow | Railway canonical | Candidate |
|---|---|---|
| Create work order | `POST /api/work-orders/draft` with `payload`, `personality`, `locale` | `POST /api/work-orders` with `data`, `narrative`, `mode` |
| Work order review/approval | `POST /api/work-orders/{wid}/review`, `POST /api/work-orders/{wid}/approve` | No equivalent operation |
| Checkout | `POST /api/checkout` expects `price_id` | `POST /api/billing/checkout` expects `plan` |
| Stripe-signed webhook | `POST /api/stripe/webhook` | `POST /api/billing/webhook` |
| Localization | `GET /api/languages`, `PATCH /api/me/locale` | No matching routes |
| CMMS sync workflow | `GET /api/cmms/adapters/status`, `GET /api/cmms/sync-queue`, `POST /api/cmms/process` | No matching routes |

Canonical register schema requires `email`, `password` and offers optional `locale`; candidate register requires `email`, `password` and offers `name`. Canonical checkout input offers `price_id` (price selection); candidate checkout input uses `plan`. **Neither is safe to translate by blindly forwarding requests.**

### Canonical-only operations

```text
GET   /api/assets/{asset_id}/history
GET   /api/billing/status
GET   /api/cmms/adapters/status
GET   /api/cmms/sync-queue
GET   /api/export/account
GET   /api/languages
GET   /api/personalities
GET   /api/work-orders/{wid}
GET   /privacy
GET   /terms
PATCH /api/me/locale
PATCH /api/work-orders/{wid}
POST  /api/checkout
POST  /api/cmms/process
POST  /api/stripe/webhook
POST  /api/work-orders/draft
POST  /api/work-orders/{wid}/answer
POST  /api/work-orders/{wid}/approve
POST  /api/work-orders/{wid}/next-question
POST  /api/work-orders/{wid}/review
```

### Candidate-only operations

```text
GET  /api/admin/status
GET  /api/health/live
GET  /api/health/ready
GET  /api/knowledge/search
POST /api/ai/handoff
POST /api/ai/troubleshoot
POST /api/ai/work-order
POST /api/auth/google
POST /api/auth/logout
POST /api/billing/checkout
POST /api/billing/portal
POST /api/billing/webhook
POST /api/work-orders
```

## Test evidence

1. Draft PR #38 CI passed its exact-route Vercel-to-Railway health and OpenAPI proxy checks. **Preview-only**, not `main`.
2. Draft PR #41 GitHub Actions run `42915029922` passed **four synthetic, in-memory candidate FastAPI tests** covering fake signup/session, owner work-order isolation, invalid billing plan, and webhook test HMAC rejection/acceptance. It did **not** test Railway's separate source, live database or real Stripe callback.
3. Railway canonical gateway/production stayed online. No live data was changed.

## Release decision: BLOCKED

**Never replace Vercel `/api/(.*)` routes with a blanket Railway rewrite or invert the direction.** A healthy gateway proxy does not imply compatible API contract, identity model, Stripe semantics or work-order lifecycle.

The lower-risk customer path is to preserve Railway's canonical API behind its existing Caddy gateway and have independently verified marketing pages link to the correct authenticated Railway application. Do not rewrite live login, checkout, webhook, DNS, or customer traffic without isolated signed-webhook and end-to-end tests, consent to any commercial change, and a verified rollback.

The temporary `/__bridge/railway-openapi` and `/__bridge/railway-health` routes exist **only on the draft preview branch** for read-only verification and should not be promoted as customer features.
