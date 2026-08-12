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

Railway runs the root Dockerfile. The container starts:

```bash
uvicorn production:app --host 0.0.0.0 --port ${PORT:-8080}
```

Production entrypoint: `backend/production.py`  
Health check: `/api/health`

Intended public routing:

- `wrenchrelay.com` and `www.wrenchrelay.com` — product choice / marketing entry
- `app.wrenchrelay.com` — app entry
- `industrial.wrenchrelay.com` — preselect Industrial
- `automotive.wrenchrelay.com` — preselect Automotive
- `api.wrenchrelay.com/api/health` — production API health

Cloudflare should provide DNS/TLS only; Railway remains the application runtime.

## Required environment variables

See `.env.example`. Never commit secrets. The important production variables are:

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

## Safety boundary

WrenchRelay is a documentation and reasoning assistant. It does **not** replace LOTO, qualified-person rules, electrical safe-work practices, guarding, OEM/service information, vehicle lifting/airbag/high-voltage procedures, engineering review, or site procedures. AI output must be verified by the technician before action or entry into an official record.

## Commissioning

Run dependency-light source checks:

```bash
python scripts/commission.py
python tests/dynamic_smoke.py
```

Then perform a real production build (Docker/Railway) and execute `ACCEPTANCE_TESTS.md` against the deployed environment.
