# Isolated durable approval ledger

This component is not wired into production or a CMMS connector. It does not
replace the previously described, currently unavailable CMMS skeleton.

Run: `python -m unittest discover -s tests/cmms_layer -v`

## Implemented contract

- Propose an immutable canonical payload, asset, source revision, before-image,
  and explicit compensation plan. Expire within 15 minutes.
- Confirm the exact hash of a human-visible proposal through authenticated UI.
  A hash alone is not evidence of a human click: the caller must enforce that.
- Generate a random approval token; persist its hash only.
- Check permission again when consuming approval. Bind token to tenant,
  approver, proposal and expiry. Record one intent with a tenant-scoped unique
  idempotency key. Concurrent consumption has one winner.
- Persist proposal, approval and intent events transactionally.
- Never execute vendor writes. INTENT_RECORDED does not mean SENT or SUCCEEDED.

## Required integration boundaries

Tenant and actor must come from verified server authentication. Authorization
callback must check current server-side membership and least privilege on each
call. Do not expose this Python API directly to untrusted HTTP parameters.
The UI must display the complete proposed diff, target asset and revision before
approval. Refresh the vendor revision server-side before recording intent; this
library cannot verify the truth of a supplied revision. Vendor-side conditional
writes would still be needed to close a check/write race.

Use a private directory on persistent local disk for the SQLite file; enforce
filesystem permissions, encryption and retention at deployment. Proposal payloads
and before-images may contain private data; minimize them. No credentials in
payloads. SQLite is not a distributed multi-writer database.

SQL triggers reject ordinary audit-event updates/deletion. A host/database
administrator can remove triggers or alter the file: this is not a tamper-proof
or independently verified audit service. Denied requests require separate
security logging at the authenticated API boundary, without tokens or secrets.

Before any future executor: add durable dispatch/result/reconciliation states,
vendor idempotency or supported preconditions, failure-injection tests at every
network boundary, and fresh acceptance authorization. An uncertain network
outcome must never be blindly retried. Compensating writes require a new reviewed
proposal and approval; storing a rollback plan does not execute or prove it.
Unsupported irreversible operations remain disabled.

Eleven local synthetic tests pass. No live credentials, human pilot results,
CMMS writes, production deployment or end-to-end authentication validation.
