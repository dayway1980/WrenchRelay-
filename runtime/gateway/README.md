# Compatible production gateway release — 2026-10-29

The existing production gateway has a working /delete-account page, but /account-deletion returns 404. Gateway-served pages also lack browser security headers already returned by the backend. This release adds aliases and independent default headers while preserving stricter upstream values.

The user authorized production rollout with: “Update production with our best changes.” This release also carries the previously tested PR #25 signing workflow through its parent commit. It does not execute a signing run or publish to Google Play.

## Exact rollout

- Railway project: 379b7e9c-79b9-4e60-bb10-42384e0134a9.
- Environment: 09ace4e5-e5a4-4f8d-a1bb-e86da3c19a8d (production).
- Gateway service: 859a81e9-b4bb-40c1-aa40-ecb249dc9442 (wrenchrelay-app), image caddy:2-alpine.
- Previous gateway deployment: bc093522-0a00-483d-9006-3a656c31a59d; reported rollback available.
- Replace only the gateway startCommand with the exact start-command.sh contents. Review the staged diff and commit only this service change.
- Preserve the backend image/archive, credentials, volumes, DNS/domain mappings, replicas, health check, overlap and draining settings.
- After deployment verify X-WrenchRelay-Release=gateway-20261029-r1; aliases return 308 to /delete-account; public pages/health succeed; unauthenticated data access and unconfigured billing remain denied.

## Validation

Twenty local isolated checks used Caddy 2.11.7 verified against its official release SHA-256. They exercised full startup materialization, all principal public pages, default headers, preservation of a stricter upstream Referrer-Policy, exact app.js bytes, 401/404 forwarding and legacy webhook rewrite/503 denial.

Local byte-parity testing used public app.js SHA-256 0e775008fe78a9b62285a75bef9a3e64544e158c0d602c84b7bf91430966f538. The existing billing-readiness guard was present and is preserved. No app source or customer records were substituted.

The read-only CI repeats the routing checks using an explicit disposable JavaScript fixture and local mock APIs. It cannot establish private production credentials or end-to-end user workflow acceptance.

## Rollback

Use the exact start-command.before.sh contents to restore the prior startCommand, verify the staged change is limited to this service, and deploy. Re-read the configuration and public health. Prior deployment ID and both complete commands are retained; do not rely on a build-only redeploy to undo a start-command change.

## Independent release boundaries

PR #25's workflow stays manual and requires verified Play identity, an owner key, a protected environment and device QA before signing/upload. Those are not supplied by merging the workflow.

The current live backend is SQLite 3.1.0-canonical-i18n, sourced from a variable-held archive. MongoDB backend candidates and larger billing changes remain outside this gateway rollout. Runtime logs show Stripe TLS verification works but usable key/signing-secret values are absent, so automatic billing remains disabled.

Cloudflare Worker build filters exclude Android and gateway-only source paths from the Worker production trigger. This avoids an unrelated Wrangler missing-entry-point deployment. The Worker script and its traffic deployment are preserved.
