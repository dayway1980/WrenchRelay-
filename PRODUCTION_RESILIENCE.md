# Production resilience and database cutover

## Target standard

- Dedicated managed MongoDB cluster that does not pause for inactivity.
- Multi-node replication, automated point-in-time recovery, encryption, and
  alerts for availability, connection saturation, storage, and replication lag.
- Separate production and staging credentials with least privilege.
- Application secrets stored only in the deployment platform.

## Zero-downtime cutover gate

1. Create the replacement cluster in the same or nearest region to the runtime.
2. Enable continuous backup and provider alerts before copying data.
3. Copy production with the provider's live-migration/continuous-sync facility.
4. Run `MONGO_URL='<candidate>' DB_NAME=wrenchrelay python scripts/verify_database.py`.
5. Compare collection counts and critical indexes between source and target.
6. Deploy a staging service against the candidate and pass `ACCEPTANCE_TESTS.md`.
7. Stop writes briefly, allow replication to reach zero lag, and take a final backup.
8. Change only `MONGO_URL` in production and deploy. Do not change public DNS.
9. Verify `/api/health/ready`, authentication, save/history, billing webhooks, and AI flows.
10. Keep the old cluster read-only for seven days. Roll back by restoring the old
   `MONGO_URL` if any verification fails.

## Incident behavior

- `/api/health/live` proves the process is alive and never depends on MongoDB.
- `/api/health/ready` returns 503 unless MongoDB is reachable; Railway uses it
  to prevent a bad release from taking production traffic.
- `/api/health` reports `degraded` for monitoring without exposing credentials.
- A database outage must page an operator; it must not trigger destructive
  retries, automatic schema changes, or a restart loop.
