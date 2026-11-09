# SQLite recovery and source reconciliation

## Release direction

Preserve the currently observed SQLite/account/session contract for the first reconciled release. The MongoDB-based 2.0.0 candidate is a separate implementation, not a drop-in upgrade. No automatic migration or traffic switch is implemented by these tools.

## Recovered evidence — October 25, 2026

The production backend reports 3.1.0-canonical-i18n and sqlite. Railway's SUCCESS deployment 415f3d9e-0d6f-4dde-9739-ea090bb75946 logged runtime TGZ SHA-256:

`74f5e3c7f7d242dcb2f45ba3d9c62d95243357b2e05adbfeb0bf2defc7199ed1`

The persistent production volume is 9f41a24b-b6a8-4656-a372-dd4d7a1d2ab4, mounted at /app/wr/data. A mounted volume is not evidence of a usable backup. The existing Cutover environment was previously documented as sharing this volume; do not use it for isolated testing without freshly verifying and separating its storage.

Three historical source ZIPs were recovered and verified against their stored checksum files:

| Source | Verified ZIP SHA-256 |
| --- | --- |
| WrenchRelay_CANONICAL_2026-09-06_I18N_IDEMPOTENT.zip | 47a7f8e0496ba8401b7bf2af2d0905456b8851dd1a293c180bb5a9bb04e5f830 |
| WrenchRelay_INDEPENDENT_PORTABLE_3.1.1_2026-09-06.zip | 8af21dd7c81e6dfcefdea49d31e0c9c318ea367b0463550386b0af067d893cf9 |
| WrenchRelay_PRODUCTION_3.3.0_2026-09-08.zip | eba5c39ecaf6f7824aa697eb14c9c9d042d20c58429d7db0bae59a5a9a0cba4a |

The i18n ZIP reports the same application version as live, but none of these ZIP checksums establishes identity with the runtime TGZ. Runtime patches and the gateway's frozen JavaScript must also be reconciled. Never substitute a historical ZIP simply because its version label matches.

The current production startup command exactly matches production_start_after.txt in WrenchRelay_Deployment_Repair_2026-10-24.zip after trimming surrounding whitespace. This ties the recorded startup procedure to the inspected service configuration, but does not recover the archive or patch variable contents.

## Confirmed compatibility differences

| Contract | Recovered historical i18n source | GitHub candidate |
| --- | --- | --- |
| Password verification | PBKDF2-SHA256 encoded hashes | bcrypt context |
| Token identity | sub=user ID, account_id and email claims | sub=email |
| Tenant records | SQLite users/work_orders use account_id | MongoDB users use email, work orders use owner |
| Client workflow | Structured draft/review/approve and CMMS queue | Different API and document shapes |

An isolated synthetic check confirmed that the candidate password context does not recognize the legacy hash. With the same synthetic signing secret, it accepts a legacy token's user-ID subject as its email identity. This does not preserve account lookup semantics. No real credentials, sessions or customer data were used.

## Guarded backup rehearsal

The historical backup.py uses sqlite3.connect on its source path, which can silently create an empty database when the path is wrong. scripts/sqlite_backup_rehearsal.py instead requires an existing database with application tables and opens it using SQLite mode=ro. It refuses an existing destination; uses the online backup API to include committed WAL content; checks database integrity, foreign keys, schema and table counts; reopens an isolated restored copy; and creates the new snapshot with permissions 0600. It prints metadata and checksums, not records. It does not install a database into a running application or change hosting configuration.

After obtaining an authorized copy in a private directory, run locally:

```bash
python scripts/sqlite_backup_rehearsal.py /private/copy.sqlite3 /private/new-snapshot.sqlite3
```

The destination must be new. Keep snapshots, database files and their contents out of GitHub. For a live WAL-mode database, use an authorized online backup, not a filesystem copy of just the main .sqlite3 file.

## Verification completed

- Seven backup-safety tests: committed WAL data, missing source, empty database, existing destination, source/destination collision, corrupt input cleanup, and foreign-key violations.
- Five original historical i18n app tests passed in its separately installed dependency environment.
- An additional temporary synthetic account/work-order rehearsal passed: snapshot and isolated restore preserved the account identity, work order and existing signed token when using the same synthetic signing secret.
- Existing 12 health/legal regression tests and 81 source commissioning checks passed locally.

These are tests on fixtures and historical source. No production backup was created, no production backup restoration was proved, and no storage migration was performed.

## Exact remaining inputs

1. The current hash-matched runtime TGZ and the nonsecret runtime patch bundles referenced by the live startup command. Connected Railway OAuth exposes their variable names, not their bytes; no authenticated Railway CLI/token was available in this workspace. Never post API keys or signing secrets to obtain source recovery.
2. An authorized consistent production SQLite snapshot, transferred through a private file channel, followed by this isolated restore check and actual application-level acceptance. Do not place customer data in public PRs.
3. A source-controlled build incorporating the exact recovered source and patches, preserving storage, session identities, human approval gates, payment safeguards and gateway routes.

Do not enable GitHub-to-Railway deployment or merge this PR as a live replacement until those release-specific checks pass.
