# WrenchRelay candidate synthetic acceptance gate · November 10, 2026

This suite exercises only the **candidate FastAPI** source at `api-service/main.py`, not the different Railway v3.1.0 SQLite runtime. It uses `mongomock` as an in-memory database and fake users/vehicles/assets.

Test intentions:
- Registration, HTTPS-only session cookie, logout and invalid JWT rejection
- Two synthetic users cannot read each other's work-order or knowledge-search data
- Anonymous access to work orders is rejected
- Unknown billing plan is rejected without initiating Stripe Checkout
- A bad webhook HMAC signature is rejected without granting an entitlement
- A synthetic signed event is recognized and updates only the fake in-memory account

**Never interpret these tests as production release approval.** They do not verify real MongoDB connectivity, account-organization semantics, Stripe event authenticity from the actual payment account, event deduplication, subscription lifecycle ordering, signed delivery, webhook raw-body handling through Caddy/Vercel, reconciliation with Railway SQLite, data migration, commercial price/tax behavior, or real customer use.

The candidate API's email-owner model is materially different from the newer organization/role model in `backend/`. Do not route real Industrial or Automotive logins or billing to candidate APIs solely because tests pass.

Environment: only GitHub Actions runner, no repository secrets referenced; no remote database or Stripe SDK API calls. Do not enable a wildcard Atlas access rule or move real customer data into the sandbox.

This test is additive to the preview routing gate in draft PR #38; that PR must remain draft until separate cutover validation and owner authorization.
