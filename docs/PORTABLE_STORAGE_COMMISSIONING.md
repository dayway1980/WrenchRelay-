# Portable storage commissioning

Status: tooling tested locally; not integrated or deployed. No new paid services authorized.

## Confirmed October 28, 2026

Railway production has a 1024 MB volume at /app/wr/data. Public health previously reports SQLite v3.1.0-canonical-i18n. Runtime starts backend.app:app from WR_SRC_00..07 archive variables. The main branch has no backend/app.py; server.py and backend/db.py use MongoDB. OAuth hides variable values, including WR_DB_PATH and source archive. Therefore the repository is not a verified reproduction of live production. Do not switch its source or apply migrations against live data.

## Deployment gates

1. Securely recover the deployed source archive, patches, dependency versions and SHA256. Never commit credentials or customer data. Establish the runtime database path inside /app/wr/data.
2. Inventory all data readers/writers, including MongoDB and recovery service, before consolidating or stopping services.
3. Take a snapshot with scripts/sqlite_snapshot.py on the host. Copy it encrypted to an independently controlled device or existing storage; keep encryption keys separate. A second file on the same volume is not disaster recovery. Do not run against production until the path and available space are confirmed.
4. Restore to an isolated directory and verify integrity, schema and representative record counts. Do not expose authentication secrets in test output. Agree retention and recovery objectives before scheduling backups. Monitor failed, stale or missing backups and disk usage.
5. Introduce migrations with rollback from a verified snapshot. Confirm work-order persistence across process restart and deployment in staging.
6. Use authenticated server-side ownership checks for every read, search, update, export and delete. Test cross-customer access denial, including guessed record IDs. Never trust a tenant ID supplied by the browser alone.
7. Keep approved knowledge separate from raw notes. Record source, permission, reviewer, approval time and revision. Search must restrict to the authenticated customer. Do not treat retrieved text as executable instructions or verified maintenance facts.
8. Support basic record save/history/export without AI or payment-provider calls. Simulate unavailable credentials/network in staging; report unavailable AI clearly without inventing generated results. Respect access entitlements.
9. Test export/deletion scope and backup retention before promising deletion behavior. Do not store payment-card data. Document actual data processors and retention accurately.
10. Only after the source matches production and staging checks pass, prepare a narrowly scoped deployment with rollback. Leave the unrelated staged TLS change intact for separate review.

## Cost review

Existing MongoDB has 10240 MB allocated; recovery has 1024 MB. Three Android builder services are present. Allocations are not measured usage or proven savings. Check runtime metrics, invoices, owners and dependencies before stopping anything. No service has been removed.

## Local validation

python -m unittest discover -s tests -p test_sqlite_snapshot.py -v

Four tests cover committed WAL restoration, restrictive file permissions, missing source, existing destination and corrupt source cleanup. These are utility tests, not production commissioning or off-host backup verification.
