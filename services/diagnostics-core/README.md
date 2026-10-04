# WrenchRelay Diagnostics Core

Production-oriented TypeScript service for structured technician intake, weak supervision, provenance-aware diagnosis, counterfactual test selection, localization bindings, and strictly human-approved CMMS interoperability.

## Why this is isolated

The current WrenchRelay repository runs a Python/FastAPI production path. This service lives under `services/diagnostics-core/` so it can be validated and deployed independently without replacing the existing entrypoint.

## Safety boundary

The system intentionally separates four stages:

1. `POST /v1/intake/analyze` — deterministic analysis plus durable provenance-ledger persistence. No external CMMS writes.
2. `POST /v1/cmms/prepare` — creates an immutable outbound draft and UI confirmation payload.
3. `POST /v1/cmms/:draftId/decision` — authenticated human approves or rejects the exact SHA-256-bound payload.
4. `POST /v1/cmms/:draftId/dispatch` — performs the provider write only after approval is revalidated.

The analysis engine has no code path that calls dispatch.

## Methodology

### Weak supervision / noisy text

`src/diagnostics.ts` uses domain labeling functions that may vote or abstain. It refines labeling-function reliability with an unlabeled EM-style estimator and explicitly discounts repeated votes from the same evidence family, reducing false confidence from correlated rules. Raw text is never overwritten: normalized forms are derived observations. Exact character-offset evidence spans, sensor fragments, and machine-code observations remain separately addressable in the provenance ledger.

### Causal/counterfactual reasoning

The engine maintains competing structural hypotheses rather than one forced diagnosis. Candidate tests have predicted signatures under each hypothesis. The next-test utility is:

`hypothesis separation - safety risk - downtime - direct cost - irreversibility - authorization penalty`

The engine may recommend a test, but medium/high-risk or operational tests remain human-authorized actions.

### Unknown mechanism

An explicit unknown-mechanism probability is maintained and rises when evidence is sparse or diffuse. This prevents the known hypothesis set from consuming 100% probability by construction.

### Provenance

The Prisma model separates:

- raw observations,
- exact evidence spans,
- derived inferences,
- inference/evidence links with signed contribution,
- human approvals,
- CMMS drafts,
- dispatch audit records,
- translation bindings,
- provenance edges.

`database/hardening.sql` makes the raw evidence, provenance edges, and human decisions append-only in PostgreSQL.

## Localization

UI output uses translation keys (`cmms.confirm.title`, `cmms.field.title`, etc.) rather than hard-coded user-facing English in workflow contracts. `TranslationBinding` supports global and tenant-specific locale bindings plus human-verification state. `src/i18n.ts` ships the confirmation workflow matrix for English, Spanish, French, German, Brazilian Portuguese, Simplified Chinese, Japanese, and Korean, with deterministic English fallback.

## Provider integration

No unverified vendor endpoint is invented. Each tenant CMMS connection stores a verified HTTPS base URL and provider configuration containing `createWorkOrderPath`, method, authentication mode, and field map. Secrets are referenced by name and resolved at runtime from the deployment secret store/environment.

Supported adapter identities:

- Fiix
- eMaint
- Maintenance Connection
- Generic REST

## Installation

```bash
cd services/diagnostics-core
cp .env.example .env
npm install
npm run prisma:validate
npm run build
npm test
```

Create the database tables with your normal Prisma migration workflow, then apply `database/hardening.sql`.

## Railway

Deploy this directory as a separate Railway service. Set `DATABASE_URL`, `WR_GATEWAY_HMAC_SECRET`, `WR_PUBLIC_BASE_URL`, and only the provider secret references needed for enabled tenants. Health check: `/healthz`.

## Vercel

The diagnostic functions are pure and can be lifted into Vercel route handlers. The CMMS bridge requires a PostgreSQL-compatible connection strategy suitable for serverless/edge execution. Keep the explicit decision/dispatch split; do not collapse it into one route.

## Existing WrenchRelay compatibility

This package does not change the current Python/FastAPI backend, MongoDB collections, React frontend, or root Dockerfile. It is designed for staged integration after validation.
