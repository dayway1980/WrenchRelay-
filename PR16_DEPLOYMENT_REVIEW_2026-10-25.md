# PR #16 deployment review — October 25, 2026

Inspection: approximately 4:41–4:48 PM America/Chicago. Reviewed head:
`70fb5a7f1f6d3c5d043ac6cbabe3d91c57b0911d`, branch
`repair/production-config-20261024`. PR remains open and draft.

## Verified results

| Path | Exact result | Practical meaning |
| --- | --- | --- |
| Vercel `wrench-relay` | `dpl_J8ewSRHnrCcXD6jxsQmarxKaztNT`, READY, matching head, non-production branch; immutable preview readiness HTTP 503, `database=not_configured` | Build succeeded; runtime/database readiness is blocked |
| Vercel `wrenchrelay-industrial` | `dpl_3zu2zj1ygh3sNrCkuEmsxvkRGVPf`, READY, matching head, non-production branch; immutable preview readiness HTTP 503, `database=not_configured` | Same separation of build success and runtime readiness |
| GitHub `container-build` | Completed successfully at 7:45 AM Central on matching head | Candidate image and isolated smoke passed; does not prove live data/session compatibility |
| GitHub `source-checks` | Completed successfully at 7:44 AM Central on matching head | Source checks passed; not a production release approval |
| Cloudflare current head | Build `8115993a-fe9f-4148-93a3-3eaf13a5bcab`, stopped with failure at 7:47 AM Central | Failure is now confirmed, rather than merely unresolved |
| Cloudflare notification commit `20e394b` | Build `0e12533c-5168-4116-a222-59856a410467`, stopped with failure at Oct 25 02:01:08 UTC (Oct 24 9:01 PM Central) | The earlier in-progress notification is superseded by completed failure evidence |

The PR's latest discussion has two bot comments: Vercel reports both previews
Ready; Cloudflare reports deployment failed on the current head. These are
provider results, not a human release approval. Each authenticated Vercel
deployment response confirms the inspected commit and has `target=null` on this
non-production branch.

## Concrete Cloudflare failure

Both authenticated logs show Wrangler 4.152.0 executing
`npx wrangler versions upload`, followed by:

> Missing entry-point to Worker script or to assets directory

Dependency installation completed first. The selected dashboard-managed
trigger is `Deploy non-production branches`, with root `/`, empty build command,
all branches included except `main`, and the upload command above. The complete
head tree contains no Wrangler configuration or Worker entrypoint. The root
React build is not invoked by that trigger.

This is an absent deployment target/build configuration, not evidence that the
legal identity or CORS correction broke Cloudflare. Other errors after a proper
target is defined remain untested. Retrying identical settings cannot resolve
the observed missing entrypoint.

`versions upload` uploads a version without promoting it to production. The
dashboard URL's `production` component is not proof that this failed attempt
changed traffic. Current deployment metadata still identifies deployment
`d05efb58-7aa8-40c3-ad59-9fadb7620b64`, created October 23, using version
`5a0ba8ba-5840-42a1-a556-617e0bf6d63a` at 100%.

## Smallest safe step performed

Read the authenticated original/current build logs, trigger configuration,
Worker settings, domains, accessible zone routes and deployment metadata.
The Worker has a fetch handler, no configured bindings or assets, and enabled
workers.dev access. The custom-domain query returned no domains. No matching
Worker routes were returned in the only visible zone (`wrenchrelay.com`,
pending). These observations do not prove ownership or routing in other
accounts. Metadata does not establish whether the Worker's code is a proxy or
another implementation; the intended app role remains unverified.

The README's intended Cloudflare DNS/TLS role conflicts with an active Worker
Git build integration. Preserve both triggers and the active Worker until its
actual role is reconciled. Do not add a placeholder Worker, attach only static
assets and lose `/api`, or replace the preview command with `wrangler deploy`.
No retry, upload, trigger edit or production routing change was needed for this
diagnosis.

## Changed files inspected

The inspected PR changes 15 files. Runtime changes preserve configured frontend
origins/URLs and correct WrenchRelay LLC defaults in both API entrypoints,
including blank settings. Other changes add commissioning assertions,
container/source CI, container smoke, legal regressions, guarded SQLite backup
and restore rehearsal, backup safety tests, and routing/cutover/recovery notes.
The current Dockerfile already copies root `requirements.txt` and preserves the
narrow Python module layout; this PR does not need a broad Docker COPY change.

Existing source/recovery notes document a separate release blocker: observed
live SQLite 3.1.0-canonical-i18n and its account/session contract differ from this
MongoDB 2.0.0 candidate. Historical fixture restores do not establish that a
consistent live backup exists or that the exact runtime archive has been
recovered. This review did not access customer records or repeat those already
completed historical rehearsals.

## Next section built

Added `scripts/release_readiness.py`, its behavior tests, an offline evidence
contract and a sanitized snapshot of this inspection. The checker requires an
explicit hosting target, full matching commit, fresh independently collected
records, successful CI, actual API/database readiness and release-specific
proofs for source, storage, sessions, backup restoration, workflows, payment
safeguards and rollback. Cloudflare is assessed separately from Vercel.

Both evaluations of the real inspected snapshot return BLOCKED (exit 2),
correctly retaining the 503 readiness and absent recovery/compatibility proofs.
Even complete synthetic evidence returns `production_approved=false`. This is
an offline consistency check, not an authenticity verifier or a newly installed
hosting release gate. Source CI tests the checker using synthetic fixtures.

Local verification: 19 release-checker tests, seven existing SQLite backup
safety tests and 81 source commissioning checks passed. A live restoration,
Cloudflare successful upload and customer workflow commissioning are not
claimed. Refresh evidence for any subsequent commit; the snapshot remains tied
to the inspected `70fb5a7` head.

Next required inputs are still the exact hash-matched live source and runtime
patches, followed by an authorized consistent SQLite snapshot in a private
channel and isolated application-level restore/compatibility evidence. See
`SQLITE_RECOVERY_REHEARSAL.md`; keep all customer data and credentials out of
the PR. No merge, production deployment, DNS/database/secret change or paid
commitment was made in this review.

## Direct evidence

- [PR #16 and current comments](https://github.com/dayway1980/WrenchRelay-/pull/16)
- [Inspected commit checks](https://github.com/dayway1980/WrenchRelay-/commit/70fb5a7f1f6d3c5d043ac6cbabe3d91c57b0911d/checks)
- [Container run](https://github.com/dayway1980/WrenchRelay-/actions/runs/40194433034)
- [Source run](https://github.com/dayway1980/WrenchRelay-/actions/runs/40194433003)
- [Vercel wrench-relay deployment](https://vercel.com/dayway1980s-projects/wrench-relay/J8ewSRHnrCcXD6jxsQmarxKaztNT)
- [Vercel industrial deployment](https://vercel.com/dayway1980s-projects/wrenchrelay-industrial/3zu2zj1ygh3sNrCkuEmsxvkRGVPf)
- [Current Cloudflare build log](https://dash.cloudflare.com/eff681f2cdce601d3f6ad13e78e96159/workers/services/view/wrenchrelay/production/builds/8115993a-fe9f-4148-93a3-3eaf13a5bcab)
- [Original Cloudflare build log](https://dash.cloudflare.com/eff681f2cdce601d3f6ad13e78e96159/workers/services/view/wrenchrelay/production/builds/0e12533c-5168-4116-a222-59856a410467)
- [Cloudflare missing configuration guidance](https://developers.cloudflare.com/workers/ci-cd/builds/troubleshoot/)
- [Cloudflare upload versus deployment semantics](https://developers.cloudflare.com/workers/versions-and-deployments/deployment-management/)
