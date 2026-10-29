# Internal Android signing workflow

This draft workflow builds an owner-reviewed source commit and creates an internal-test candidate. It does not contact Play Console, upload to Google Play, publish an app, or change hosting.

## Review and commissioning

1. Review and merge this workflow separately from app code only after evaluating automatic main-branch hosting deployments. This task does not authorize that merge.
2. Configure the GitHub environment `play-internal-signing` with required owner reviewers and restrict its deployment branch to the default branch. A named environment alone does not configure those protections.
3. Store the owner upload keystore and credentials as environment secrets: `PLAY_UPLOAD_KEYSTORE_B64`, `PLAY_STORE_PASSWORD`, `PLAY_KEY_PASSWORD`, and `PLAY_KEY_ALIAS`. Never put them in source, chat, issue comments, or public build artifacts.
4. Read the exact app package, an unused versionCode, and the **upload certificate** SHA-256 from the existing Play Console app. These are not established by source-code defaults or passing input checks.
5. Select the full 40-character lowercase SHA of reviewed Android source in this repository. The source must support the requested Gradle package/version overrides. PR #14 contains the app candidate; this workflow does not merge or choose it.
6. Run the workflow manually from the default branch with the reviewed source SHA and verified Play inputs. No other branch can start the build/sign jobs.
7. Approve the protected signing environment only after checking the requested source and identity. Download the signed artifact, verify `SHA256SUMS.txt`, and review `RELEASE_IDENTITY.json`.
8. Complete physical-device, authentication, voice, privacy/account-deletion and internal-track validation before any separate upload or publication.

## Checks performed

- PR validation tests inputs, compiled-manifest mismatches, signature verification and cleanup using disposable regression keys.
- The unsigned build runs on a separate runner with no owner upload-key secrets.
- Source selection requires a full immutable commit SHA and the checkout must match it exactly.
- A separate signing runner downloads only the unsigned artifact from the same run by immutable artifact ID. It never executes the selected app's Gradle code.
- Google bundletool 1.18.3 is checked against its official release-asset SHA-256 before execution. It validates the bundle and reads the compiled manifest. Wrong package, version or existing signature blocks signing.
- The validated manifest identity is bound to the unsigned bundle SHA-256. The signing helper checks both immediately before writing the key.
- Owner secrets are exposed only to the signing step. The keystore lives in a private temporary directory with cleanup on exit; an always-run cleanup also removes signing intermediates.
- The signed bundle must pass strict JAR signature verification against the owner keystore and match the expected public certificate fingerprint.
- Output records the selected source commit and workflow commit separately. Signed artifacts are retained for seven days; unsigned artifacts for one.

## Limits

Passing structural checks is not proof of Play ownership, package availability, unused versionCode, environment approval configuration, or app/device readiness. None of the build/sign jobs runs on a pull request. Missing owner credentials fail closed. A hard-killed runner is disposed of by GitHub; shell traps cannot run after an uncatchable process or machine termination.

The Cloudflare non-production build trigger excludes only `release/play-signing-gate-20261028` because it contains no Worker deployment source. Its historical failed check is retained. Re-evaluate that exclusion if Worker source is added.

