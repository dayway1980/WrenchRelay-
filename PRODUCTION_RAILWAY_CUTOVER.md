# Railway production cutover safety checklist

This repository is **not currently the direct deploy source for the live WrenchRelay Railway services**. The production backend is running an image-based Python 3.11 container that reconstructs a separately packaged application from environment variables. The production gateway runs a separately configured Caddy image. A passing test on this repository alone **does not authorize a production source switch**.

## Before enabling GitHub-to-Railway automatic deploys

1. Identify the authoritative WrenchRelay production project, environment, backend, gateway, and volumes. Record the currently successful deployments and their startup/healthcheck config.
2. Back up production MongoDB and attached volumes using a proven restoration procedure. Do not export secrets into GitHub or logs.
3. Compare live packaged backend, Caddy routing, voice assets, privacy/account-deletion pages, payment fail-closed logic, and account/session behavior against the candidate commit. Treat discrepancies as blockers.
4. Build this repository's Dockerfile in a **non-production** environment with its actual runtime requirements. Verify Python dependencies, API, static assets, health endpoints, and persistence separately.
5. Run `python commission.py`, existing tests and commissioning smoke checks, then manually test registration/login, voice-to-work-order, save/retrieve, human verification, Google sign-in if configured, and Stripe checkout/webhook with safe test credentials. No test may generate customer charges.
6. Validate all active custom domains at the **authoritative** DNS provider. Do not repoint `app.wrenchrelay.com` merely because Railway lists it as unverified; it currently serves a separate shop portal and could be controlled by another deployment. Preserve mail and TXT records.
7. Only after matching behavior and explicit cutover approval, change the source/traffic using a reversible release with measured rollback. Do not delete old services or volumes during verification.

## Confirmed issues to track

- Railway reported `wrenchrelay.app` unverified and certificate issuance incomplete.
- Railway reported `app.wrenchrelay.com` unverified with routing DNS mismatch; the public website displayed a separate shop portal.
- Current Railway OAuth connection can **list and read** the production project, but connection permanence is not guaranteed.
- Live production `GOOGLE_CLIENT_ID` was not present in the Railway gateway/backend variable-name inventories; confirm the deployed sign-in method before offering Google login.
- Stripe variable names were present, but successful checkout/webhook commissioning and actual revenue have not been independently validated.

No new paid service, DNS change, secret rotation, or production restart is required to run these source checks.
