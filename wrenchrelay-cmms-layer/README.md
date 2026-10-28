# WrenchRelay CMMS Foundation 0.1.0

**NEW RECONSTRUCTION — SYNTHETIC-TESTED — NOT DEPLOYED — NO VENDOR WRITES**

Entry point for status and all related work: `../WRENCHRELAY_START_HERE.md`.

The missing earlier Python skeleton was not recovered. This increment creates a
small new standard-library foundation instead of promoting an old ZIP.

`wrenchrelay_cmms/evidence.py`: immutable fact records with tenant, asset,
source record/field/revision and observation/retrieval times. Reject wrong
scope, missing provenance, duplicate IDs, stale and invalid time sequences.
Assess explicit evidence links, retain contradictions, abstain conservatively.
Diagnosis stays UNRESOLVED. No numeric diagnostic probability is fabricated.
Semantic support and source authenticity still require validation; nonempty
provenance strings alone do not establish truth. No hypothesis ranking yet.

`wrenchrelay_cmms/fiix_readonly.py`: sandbox-only signed FindRequest builder
for minimal Asset and WorkOrder fields. No HTTP transport exists. No production
endpoint, RPC, batch, upload or write methods. Secrets are hidden from object
repr, but signed URL/header attributes remain sensitive: never log them.
Synthetic signing checks test the official algorithm convention, not live
vendor compatibility. API clientVersion, sandbox host conventions, field
availability, access restrictions and response mapping need real acceptance.

Future transport must bind credential/endpoint to authenticated tenant and
authorized sandbox, enforce TLS and no redirects, bounded timeouts/retries,
per-tenant quotas, and operation allowlists before any network call. A sandbox
hostname is not evidence of permission. Preserve the current offline default.

10 local synthetic tests pass. See root index for separate durable approval,
backup and evaluation work. No live credentials or real pilot metrics.
