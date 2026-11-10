# Vercel candidate database readiness — November 10, 2026

## Observed
- Both `wrenchrelay-industrial` and `wrench-relay` have production-targeted Vercel builds in READY state at Git commit `8242a68b350136837c245ccf369eaab28362a6ce`.
- Both `/api/health/ready` endpoints returned HTTP 503 and `database: not_configured`.
- `wrenchrelay-industrial` has no listed `MONGO_URL` or `MONGODB_URI` variable.
- `wrench-relay` lists `MONGO_URL` and `DB_NAME` as sensitive variables. The connected API did **not** decrypt their values; do not infer their values are blank or valid.
- The standalone Railway production application runs from a separately packaged Python image, with a persistent SQLite volume. GitHub's candidate uses MongoDB; **not equivalent deployment sources or schemas**.

## Release gates before enabling customer workflows
1. Provision or select an **isolated** MongoDB instance and database, separate from canonical SQLite and live customer data. Confirm authorized costs, network allowlist, backups, isolation and rollback first.
2. In Vercel's project settings, configure the approved connection under `MONGO_URL` (or `MONGODB_URI`), `DB_NAME`, and a unique secret `JWT_SECRET`. Do not place credentials in Git, logs, issues or PR text. Do not copy the live Railway application's credentials.
3. Redeploy a **preview** and verify `/api/health/live` succeeds and `/api/health/ready` returns `database: ok`. Confirm real authentication, multi-tenant isolation and session boundaries before exposing a production URL.
4. Verify signup and account recovery without customer data; test Stripe separately with test keys and real signed sandbox webhooks. Never infer payment readiness from a healthy DB.
5. Keep Railway on its existing image+SQLite application until a reviewed byte-for-byte runtime source snapshot, tested restore and explicit SQLite-to-candidate migration plan exist.

## Code guard
Candidate entrypoints now treat a missing, empty or whitespace-only `DB_NAME` as the default `wrenchrelay` and use `WrenchRelay LLC` for a missing, empty or whitespace-only legal-entity name. These changes **do not create a database or establish connectivity**.
