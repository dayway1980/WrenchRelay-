# WrenchRelay

WrenchRelay is a voice-first maintenance documentation and troubleshooting assistant for **industrial** and **automotive** users.

## Product flow

1. Choice-first landing page: Industrial or Automotive.
2. Google sign-in when `GOOGLE_CLIENT_ID` is configured; password auth remains available as a fallback.
3. Voice or typed technician notes.
4. Generate one of three outputs: CMMS-ready work order, evidence-ranked troubleshooting plan, or shift/technician handoff.
5. Human verification before action or saving.
6. Saved work-order history and search.
7. Stripe subscription checkout/portal for paid plans.
8. `@bravatile.com` accounts receive Pro Lifetime entitlement via the configured Brava workforce program.

## Production architecture

This repository's candidate Dockerfile starts the following container. The
recorded live Railway deployment uses a separately packaged SQLite application
and Caddy gateway; it does not run this GitHub Dockerfile. See
[release parity](RELEASE_PARITY_2026-10-25.md) and
[SQLite recovery](SQLITE_RECOVERY_REHEARSAL.md) before changing the live source.

Candidate container command:

```bash
uvicorn production:app --host 0.0.0.0 --port ${PORT:-8080}
```

Candidate entrypoint: `backend/production.py`

Deployment readiness check: `/api/health/ready`

Process liveness check: `/api/health/live`

External status check: `/api/health`

Historical routing intentions (not verified ownership or current routing; see
[the domain routing matrix](DOMAIN_ROUTING_MATRIX_2026-10-24.md)):

- `wrenchrelay.com` and `www.wrenchrelay.com` — product choice / marketing entry
- `app.wrenchrelay.com` — app entry
- `industrial.wrenchrelay.com` — preselect Industrial
- `automotive.wrenchrelay.com` — preselect Automotive
- `api.wrenchrelay.com/api/health` — production API health

The documented Cloudflare role is DNS/TLS. A separate dashboard-managed Worker
build trigger also exists; its current build fails because no Worker entrypoint
or assets directory is configured. Do not add an arbitrary Worker or substitute
`wrangler deploy` on a non-production branch to make that check green.

## Required environment variables

See `.env.example`. Never commit secrets. The important candidate variables are:

- `MONGO_URL` or `MONGODB_URI`
- `JWT_SECRET`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `CORS_ORIGINS`
- `FRONTEND_URL`
- `GOOGLE_CLIENT_ID` (for Google sign-in)
- `STRIPE_SECRET_KEY_LIVE`
- `STRIPE_PRICE_WRENCH_STARTER`
- `STRIPE_PRICE_WRENCH_PRO`
- `STRIPE_WEBHOOK_SECRET`
- `BRAVA_DOMAIN` or `BRAVA_EMAIL_DOMAIN`
- `BRAVA_LIFETIME_EMAILS` (optional explicit allow-list)
- `LEGAL_ENTITY_NAME`
- `LEGAL_EMAIL`

The candidate persistence layer is selected by `MONGO_URL`/`MONGODB_URI`; no
application code or customer-facing DNS change is required to move between
compatible managed MongoDB providers. This does not migrate the current SQLite
production data or preserve its account/session contract. Follow
`SQLITE_RECOVERY_REHEARSAL.md` before proposing a storage or source change.

## Safety boundary

WrenchRelay is a documentation and reasoning assistant. It does **not** replace LOTO, qualified-person rules, electrical safe-work practices, guarding, OEM/service information, vehicle lifting/airbag/high-voltage procedures, engineering review, or site procedures. AI output must be verified by the technician before action or entry into an official record.

## Commissioning

Run dependency-light source checks:

```bash
python commission.py
python dynamic_smoke.py
```

Then perform a real production build (Docker/Railway) and execute `ACCEPTANCE_TESTS.md` against the deployed environment.

Build success is not release approval. Use the offline
[release evidence checker](RELEASE_READINESS.md) to assess fresh evidence for an
exact commit and explicit hosting target. The checker never deploys or grants
production approval; its CI tests exercise synthetic evidence only.
