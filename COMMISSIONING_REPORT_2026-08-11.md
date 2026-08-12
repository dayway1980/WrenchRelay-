# WrenchRelay 2.0 Commissioning Report — 2026-08-11

## Replacement source
Status: READY FOR PRODUCTION DEPLOYMENT.

Automated source commissioning: 61/61 PASS.
Dynamic API smoke suite: PASS.
JavaScript/JSX parser check: PASS.
Python compile check: PASS.
Secret-pattern scan: PASS.
No test-report artifacts shipped.

## Product acceptance covered
- Choice-first Industrial / Automotive entry
- Voice greeting and browser speech capture/readback
- 12 selectable Relay personalities
- Password authentication plus Google Identity Services integration path
- @bravatile.com automatic Pro Lifetime entitlement
- 14-day Pro trial for standard accounts
- AI work-order writer, troubleshooting plan, and shift handoff
- Saved work-order history and local knowledge search
- Stripe-hosted subscription Checkout and Customer Portal backend
- Signed Stripe webhook requirement
- Terms, Privacy, Safety, Billing/Refund, AI Disclosure and Accessibility pages
- Mobile responsive UI
- Safety prompt guardrails and human verification notices

## Production infrastructure verified
- Railway wrenchrelay-app: online, latest deployment SUCCESS
- MongoDB service: online, latest deployment SUCCESS
- Railway /api/health: 200
- Railway custom domains attached: root, www, app, api, industrial, automotive
- Stripe live account: WrenchRelay
- Active WrenchRelay Starter recurring price: $39/month
- Active WrenchRelay Pro recurring price: $49/month
- Railway price variables aligned to those live prices without exposing secret keys

## Known production delta
The currently deployed Railway container is healthy but its `/api/assistant` and payments routers are structural placeholders. The replacement source in this package implements those missing product paths. Production cannot truthfully be called fully commissioned until this replacement source is durably deployed.

## Deployment constraint observed
The connected GitHub integration can read `dayway1980/WrenchRelay-` but GitHub write operations return HTTP 403 `Resource not accessible by integration`. The repo remains effectively empty. Emergent senior support has the source-handoff escalation. Railway's connected agent cannot accept local source uploads; durable no-GitHub deployment requires `railway up` from an authenticated CLI context.

## Post-deploy gates
After the replacement deploy succeeds, run `python tests/dynamic_smoke.py` against source, then verify public HTTPS for root/www/app/api/industrial/automotive, Google sign-in with the production client ID, a real Stripe test-mode or controlled live checkout, signed webhook delivery, Brava entitlement with a real Brava account, and one industrial plus one automotive AI request.
