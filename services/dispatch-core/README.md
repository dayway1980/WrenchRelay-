# Dispatch core: isolated launch integration

This directory stages Module 1 of the WrenchRelay launch package inside the existing repository. It is a pure server-side library and Google Routes read adapter, not a deployed dispatch service. It has no HTTP listener, database client, payment operation, CMMS write, automatic technician assignment or stock reservation.

## Run

Use Node 24.22.1 in this directory:

    npm ci --ignore-scripts --no-audit --no-fund
    npm run build
    npm test

The dependency tree is pinned by package-lock.json with package integrity hashes. CI installs with npm ci and lifecycle scripts disabled. No secrets are needed for tests. Google calls in tests use synthetic HTTP responses; actual traffic/vendor integration is unverified.

## Contract

Call matchDispatch(unknown) only after deriving tenant, job, certified skills, legal transit permissions, vehicle remaining capacity, inventory allocations, prices and FX from trusted server sources. Mobile-supplied snapshots cannot authorize an assignment. Coordinates are technician snapshots; Google Matrix inputs include independently resolved job/warehouse coordinates.

Hard constraints reject incompatible skill vectors, language tags, transit/destination permissions, weight/volume, stale/future snapshots, absent parts/routes/FX, impossible job windows and shift overruns. The lexicographic objective is earliest completion, then missing-parts plus dispatch cost, then meters, then stable IDs. It is exact only over the supplied single-job, at-most-one-pickup feasible set. It is not a global multi-job optimizer.

Money uses decimal integer strings and bigint rational minor-unit FX with per-unit upward rounding. Include currency exponent differences in numerator/denominator. Fees, duties, taxes and tolls are not automatically added. UTC instants drive scheduling; IANA zones drive display. Resolve ambiguous/nonexistent local DST times before submitting UTC scheduling windows.

Google Matrix errors and missing compliance approvals never become zero-distance routes. The adapter requests TRAFFIC_AWARE_OPTIMAL in batches of at most 100 elements, caps each operation at 10,000 elements, restricts its endpoint, disallows redirects and bounds request time and response size. Use restricted server-only Routes credentials and quota alerts. Provider failure queues human dispatch rather than silently using stale data.

A result is only a SNAPSHOT_RECOMMENDATION. It expires within 15 seconds and no later than the earliest relevant snapshot TTL. An unrelated stale route does not shorten a candidate's validity. Before commitment, authenticate the dispatcher, enforce tenant/role scope, reread the job, compare-and-swap technician and allocated-stock versions in a transaction, and reserve external vendor inventory through an idempotent recoverable saga. Preserve the founder's human-verification boundary before CMMS writes. This branch intentionally does not introduce a second database or expose an unauthenticated route.

## Existing-app compatibility and remaining gates

The existing FastAPI runtime, Dockerfile, storage, Stripe routes and Android shell are unchanged. Current source Android package is com.wrenchrelay.industrial; the launch package used com.wrenchrelayllc.industrial. Resolve the real Play Console identity before signing/uploading, and never reuse another app's key to hide that mismatch.

The open deployment PR records SQLite-versus-MongoDB runtime parity and database-readiness blockers; adding this library does not resolve them. Do not merge/deploy this branch as evidence that signup, paid access, live inventory, location tracking or Play review is commissioned.

Acceptance for this slice: strict TypeScript compilation, deterministic eligibility/objective/security/time/currency tests, bounded Matrix adapter contract tests, immutable commit-linked CI evidence, and a diff limited to this directory and its own workflow. Capture actual CI results in the PR before deciding whether to advance integration.
