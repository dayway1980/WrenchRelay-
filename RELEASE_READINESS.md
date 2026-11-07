# Release evidence checker

`scripts/release_readiness.py` is an offline assessment of independently collected
evidence. It distinguishes a completed build from database readiness and from
production authorization. It makes no network requests, loads no application
code or environment secrets, and cannot change hosting, DNS, databases, billing
or release approval. It is not an authenticity verifier or a configured hosting
release gate. CI exercises its behavior on synthetic evidence only.

## Current evidence

`deployment-evidence/pr16-2026-10-25.json` records the inspected PR #16 head
`70fb5a7f1f6d3c5d043ac6cbabe3d91c57b0911d`. Both Vercel builds are READY;
both preview readiness requests returned HTTP 503 with `database=not_configured`.
Cloudflare failed before a successful version upload because no Worker
entrypoint or assets directory was configured. The original notification's
`20e394b` build also completed with the same error.

The known sample must report BLOCKED. Refresh evidence for a later commit
instead of relabeling this historical snapshot. Missing recovery and
compatibility proofs are deliberate gaps, not successful checks.

```bash
python scripts/release_readiness.py deployment-evidence/pr16-2026-10-25.json \
  --commit 70fb5a7f1f6d3c5d043ac6cbabe3d91c57b0911d --target vercel
```

Choose `--target cloudflare` to assess that path independently. Vercel success
never satisfies a Cloudflare build. A failed, unselected Worker build is
reported separately; it does not establish failure of the Vercel build.

## Evidence contract, schema version 1

| Field | Required evidence |
| --- | --- |
| `schema_version`, `candidate_commit`, `observed_at` | Version 1, full lowercase 40-character SHA, timezone-aware inspection time |
| `github` | `commit`, `observed_at`, `source`; one completed successful check each named `source-checks` and `container-build` in `checks` |
| `vercel` | One record per `wrench-relay` and `wrenchrelay-industrial`, each with `project`, `commit`, `observed_at`, `source`, `state=READY`, `environment=preview` |
| Vercel `readiness` | A separate record with `commit`, `observed_at`, `source`, `http_status=200`, `database=ok`, from the immutable deployment's `/api/health/ready` response |
| `cloudflare` | `commit`, `observed_at`, `source`, `state`; when selected, `state=success`, `scope=non-production-version-upload`, and a separate `readiness` record under the same contract |
| `proofs` | Records for `source_parity`, `storage_compatibility`, `session_compatibility`, `backup_restore`, `customer_workflows`, `payment_safeguards`, `rollback` |
| Each proof | `commit`, `observed_at`, `source` referencing the actual verification artifact, `result=passed` only after independent verification |

Inspection records must be no older than four hours and no more than five
minutes in the future. All selected path, CI and prerequisite evidence must
match the explicit candidate SHA. Each nested readiness observation is checked
separately. Ambiguous duplicates, malformed records, missing references,
non-success CI, and absent proofs block the assessment. `source` is a nonempty
reference to be reviewed by a person; the checker does not authenticate it or
fetch its contents. Private evidence may stay private; never put database rows,
session tokens, credentials or signed access URLs in the JSON or public PR.

Collect host metadata and health from the same immutable deployment. Do not use
a movable branch alias as the only evidence tying runtime health to a commit.
Use isolated fixtures and test payment credentials for workflow verification.
Do not connect previews to customer storage to make readiness pass.

## Decisions and verification

- Exit 0: supplied technical checks passed; `production_approved` remains false.
- Exit 2: BLOCKED; `blockers` lists missing or failed checks.
- Exit 3: invalid/unreadable JSON or invalid candidate; input contents are not echoed.

Run the behavior tests with:

```bash
python -m unittest discover -s tests -p test_release_readiness.py
```

Production approval remains a separate human decision after release-specific
source recovery, an authorized consistent SQLite snapshot and isolated restore,
storage/session compatibility, customer acceptance and a proven rollback. The
checker does not obtain those missing inputs. See `SQLITE_RECOVERY_REHEARSAL.md`.
