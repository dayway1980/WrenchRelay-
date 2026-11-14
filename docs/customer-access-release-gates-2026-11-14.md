# WrenchRelay customer-access release gates — 2026-11-14

Status: DRAFT; NOT production-approved. Evidence required for each gate. No live payment or customer-data testing without approval.

## Source observations
- src/App.js implements login/register via /api/auth/*, Google identity via /api/auth/google, session handling, checkout via /api/billing/checkout, and billing portal via /api/billing/portal.
- These frontend calls do not prove backend routes, database persistence, webhook handling, or production customer access.
- Vercel READY build status does not prove end-to-end behavior. Vercel project protection settings may affect preview URLs.

## Required release gates
1. **Public access:** From unauthenticated mobile and desktop networks, load canonical HTTPS home, automotive and industrial landing pages; verify correct routing, certificate, no SSO wall on customer domain, privacy and terms links.
2. **Account:** Register new test account; verify email ownership if required; log out, log in, reset password, and verify session expiry and rate limits. No cross-account data leakage.
3. **Persistence:** Create an authorized test record, refresh/re-login, confirm record persists; verify isolation between two test accounts. No test records in real customer accounts.
4. **Checkout:** Stripe test-mode checkout for approved pilot or plan; cancel checkout; retry webhook delivery; verify signature, idempotency, account entitlement, and billing portal cancellation. Never claim live payment readiness from test-mode success.
5. **Automotive fulfillment:** Authorized test call routed to sandbox/test number; confirm transcript/intake accuracy, handoff, fallback on service failure, customer-visible status, and human review.
6. **Industrial safety:** Output is evidence-labeled, cannot control machinery, requires human verification; ambiguous or hazardous inputs trigger abstention/escalation.
7. **Resilience:** Simulate API timeout, 429, 500, offline/mobile refresh; show actionable error, prevent duplicate submission, preserve draft where feasible, and recover without silent data loss.
8. **Operations:** Alerts, logs without secrets, backups/restore exercise, incident owner, rollback, and uptime measurement.
9. **UX/accessibility:** Keyboard operation, mobile viewport, clear focus, contrast, readable states, plain-language errors, obvious next action, WCAG 2.2 AA review.

## Release decision
BLOCKED until all critical gates have dated evidence and independent review. Record for each: environment, exact URL, test account identifier (nonsecret), test time, observed outcome, screenshot/log reference, tester, remediation owner. Never label 'works every time' or '99.9% achieved' without measurement.

## Next safe implementation step
Trace /api/auth and /api/billing from the actual production backend, identify canonical domain and current deployment, then add automated smoke tests in a separate PR. Do not change DNS, secrets, billing, deployment, or live permissions as part of this document.
