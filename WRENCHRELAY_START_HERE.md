# WrenchRelay: start here

Updated 2026-10-28. Owner: WrenchRelay LLC. **Not a production release.**

## New work, easy to locate

| Location | Purpose | Verified status |
| --- | --- | --- |
| wrenchrelay-cmms-layer/ | New evidence validation and Fiix sandbox request preparation | 10 local synthetic tests passed; no transport or live credentials |
| cmms_layer/ | Durable approval intent ledger (PR #22) | 11 local synthetic tests passed; no vendor executor |
| PR #20 | Portable SQLite snapshot utility | 4 local utility tests passed; not integrated |
| PR #21 | Descriptive pilot evaluation and acceptance protocol | 6 local synthetic tests passed; no pilot measurements |

The hyphenated directory is the NEW reconstruction, not recovery of the missing
23-test skeleton. The underscore directory contains the separately reviewed
approval component. Keep these labels until a tested packaging integration
consolidates them. No old archive has been promoted to production.

## Missing pieces, explicitly tracked

- BLOCKED: checksum-verified current runtime archive, secret-safe source recovery,
  reproducible build and source-to-deployment correspondence.
- IMPLEMENTED ISOLATED: evidence admissibility, stale/wrong-asset abstention,
  unresolved diagnosis, sandbox FindRequest signing, approval intent storage.
- NOT IMPLEMENTED: Fiix transport, provisioning/tenant binding, API-version
  acceptance, paging loop, response normalization, per-tenant rate budgeting,
  credential lifecycle, and live acceptance. Request preparation is not a connector.
- NOT IMPLEMENTED: evidence persistence, hypothesis ranking/calibration, voice
  capture/review UI, authenticated API integration and cross-tenant end-to-end tests.
- BLOCKED: authorized Fiix sandbox and consenting plant users/data. No customer
  or vendor-wide datasets have been acquired.
- UNVERIFIED LIVE: backups/restores, customer workflows, billing lifecycle and
  durable write-back. Existing app storage is not replaced by these modules.
- DISABLED BY DESIGN: CMMS external writes and autonomous diagnosis confirmation.

## Source evidence inspected

Connected Google Drive searches: WrenchRelay and Fiix; targeted Gmail searches
for repository/sandbox/Fiix terms. These are scoped searches, not an exhaustive
scan of all Google services, Drive files, browser history or the public web.

- Integration-first strategy, 2026-10-20:
  https://docs.google.com/document/d/1UAwbScWi4SVvhuQV-o9Wu3hT8hoOOkOcK6x45eS86_4/edit
- Internal Repository Sync, modified 2026-09-11 (historical, not current health):
  https://docs.google.com/document/d/12FuHBUiWijIHhiAQ30GYhgyKVyt2ZUxcvjLazdZ-PV4/edit
- Recovery plan and release gates, modified 2026-10-17 (historical):
  https://docs.google.com/document/d/13A0KkekUx99Xrm6ivjZUQeDiEvtSaBPN5MIXB8vI7J4/edit
- Official Fiix request conventions:
  https://fiixlabs.github.io/api-documentation/guide-nosdk.html
- Official sandbox eligibility and account-scoped credentials:
  https://fiixlabs.github.io/api-documentation/guide.html

The previously recorded Repository Sync URL ending E8Q2uB7Jf5YxE returned 404;
the link above was rediscovered in Drive. Historical availability, credentials,
prices and release statements require current independent verification.

## Test commands

```
PYTHONPATH=wrenchrelay-cmms-layer python -m unittest discover -s wrenchrelay-cmms-layer/tests -v
python -m unittest discover -s tests/cmms_layer -v
```

No charges, production changes, credentials or customer data are part of this
reconstruction. Unit tests are execution evidence, not independent certification.
