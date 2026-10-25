# WrenchRelay release validation — October 25, 2026

Candidate base: d9e0ddd46a8fab598bd39c83c5c24edc87a4df15, PR #16.

## Confirmed checks

- GitHub container build and smoke passed on this base, including default startup, static assets, exact Python entrypoint and isolated MongoDB readiness.
- Source commissioning passed. Both Vercel preview builds report READY.
- The current Dockerfile already uses root requirements.txt and preserves backend/production.py. PR #2's broad COPY remains unsuitable.

## Production parity blocker

Read-only checks around 07:31 Central found that both www.wrenchrelayllc.com and the Railway production backend return HTTP 200 from /api/health with version 3.1.0-canonical-i18n and database sqlite. Both return 404 from /api/health/live and /api/health/ready.

The GitHub/Vercel candidate reports version 2.0.0. Both previews return HTTP 503 from /api/health/ready with database not_configured. The Docker/Vercel candidate uses MongoDB. A successful build does not establish compatible storage, authentication, data migration or customer workflow behavior.

Railway confirms the backend source is python:3.11-slim with startup code reconstructing an archive from WR_SRC variables and applying runtime patches. The gateway source is caddy:2-alpine with a custom startup command. Neither is this GitHub Dockerfile. No staged changes were present on these services at inspection.

Rollback references observed: backend deployment 415f3d9e-0d6f-4dde-9739-ea090bb75946 and gateway deployment aa1bbd2c-d7b8-4068-b4db-fa0605593da5, both SUCCESS and reported rollback-capable. Backup restoration was not tested.

## Follow-up repair

The wrench-relay preview returned an empty legal_entity despite the corrected missing-variable fallback. An explicitly empty environment value reproduced this behavior locally. Both Python API defaults now handle missing, empty and whitespace settings while preserving a configured operator. Regression tests cover both entrypoints.

## Next release steps

1. Preserve the existing SQLite data and prove a backup can be restored in isolation.
2. Reconcile the live archive and runtime patches with source control before replacing the backend. OAuth exposes variable names only; the live archive bytes were not obtained in this review.
3. Choose and implement storage compatibility: preserve the current SQLite contract or perform an explicit, tested MongoDB migration. Do not point previews at customer data to make readiness green.
4. Verify authentication/session compatibility, customer history, voice workflows, human verification and payment safeguards on an isolated candidate.
5. Require release-specific acceptance and rollback evidence before moving traffic.

Cloudflare's Workers build check still fails for the candidate. No authenticated build log was inspected in this review, so its cause is unconfirmed and separate from the successful Docker/Vercel builds.

No production deployment, database write, DNS update, credential change or paid service was performed.
