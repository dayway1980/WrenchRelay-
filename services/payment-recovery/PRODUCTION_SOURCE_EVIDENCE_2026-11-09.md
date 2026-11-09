# WrenchRelay production source parity checkpoint — 2026-11-09

Status: READ-ONLY EVIDENCE. Release gate remains CLOSED. No production deployment, credential edit, billing activation, database change, or customer charge was made.

## Connected Railway evidence

- Project: `wrenchrelay` (`379b7e9c-79b9-4e60-bb10-42384e0134a9`).
- Environment: `production` (`09ace4e5-e5a4-4f8d-a1bb-e86da3c19a8d`).
- Running backend service: `wrenchrelay-production` (`2f75f09f-1c8c-4ce6-ae85-425aeaa35627`).
- Running deployment: `66def56e-c223-41d9-ab45-576540a04348`, SUCCESS, created November 5, 2026.
- Source image: `python:3.12-slim`; its configured startup command reconstructs an application from `WR_SRC_00` through `WR_SRC_07`, verifies a source archive checksum, and applies runtime patches.
- Reconstructed runtime root: `/tmp/wr-runtime`.
- Archived source file: `/tmp/wr-canonical.tgz`.
- Virtualenv: `/tmp/wr-venv`.
- Mounted persistent volume: `/app/wr/data` (1 GiB).
- Archive SHA-256 printed by that deployment on 2026-11-05T16:15:24Z: `74f5e3c7f7d242dcb2f45ba3d9c62d95243357b2e05adbfeb0bf2defc7199ed1`.
- No currently staged production changes.
- Recent /api/health request logs return 200. These prove availability, not authenticated workflows, billing fulfillment, or database safety.
- OAuth Railway tools expose variable **names** but withhold variable **values**. `WR_SRC_00`–`WR_SRC_07`, `WR_CANONICAL_TGZ_SHA256`, and `WR_DB_PATH` variable names are present, but the SQLite database's exact file path is not established from these metadata.
- Startup billing diagnostic reports named Stripe key and webhook variables present, `webhook_secret_format=true`, but `live_key_format=false` (unresolved; does not by itself prove the key is invalid). Do not print or rotate hidden credentials merely because this flag differs.

## Owner-side, read-only check (does not reveal any variables)

Using Railway CLI authenticated as a project owner with the required SSH key registered, run on a trusted machine:

```bash
railway ssh --project 379b7e9c-79b9-4e60-bb10-42384e0134a9 \
  --service wrenchrelay-production --environment production -- \
  sha256sum /tmp/wr-canonical.tgz /tmp/wr-runtime/backend/app.py
```

The first checksum should match the deployment log's archive hash above. The second is the **post-patch actual running app.py** checksum needed for `WR_PAYMENTS_HOST_SHA256` after independent source review. Comparing hashes alone does not prove the source is safe.

Check that the source and volume are mounted:

```bash
railway ssh --project 379b7e9c-79b9-4e60-bb10-42384e0134a9 \
  --service wrenchrelay-production --environment production -- \
  sh -lc 'test -f /tmp/wr-runtime/backend/app.py && test -d /app/wr/data && printf "source and volume present\n"'
```

Do **not** run `env`, `printenv`, or `echo "$WR_SRC_00"`; do not paste base64 chunks, private credentials, database files or customer records into chat, issues or CI logs. Only hashes and non-secret verification outcomes are appropriate for the PR.

## Remaining blocking work

1. Review the post-patch `backend/app.py` and find the true configured DB_PATH from the running application. A startup archive hash alone does not establish live source parity.
2. Identify the correct SQLite file on the mounted volume, create a secure consistent snapshot, and verify an **independent restore** (not merely a file integrity check).
3. Prove real Stripe-signed sandbox webhook processing and correct account/price ownership with an isolated restored database. This is distinct from the passing synthetic integration tests.
4. Verify authentication, checkout idempotency, subscription lifecycle and paid-feature enforcement. Preserve the existing authorized trial and lifetime entitlements.
5. Stage only the reviewed SQLite-compatible patch, retain an explicit rollback path, obtain the required Railway deployment approval, and keep payments fail-closed until end-to-end acceptance.

GitHub PR: https://github.com/dayway1980/WrenchRelay-/pull/19
