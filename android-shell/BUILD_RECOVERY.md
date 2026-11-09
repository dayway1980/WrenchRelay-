# Android build recovery and release gates

Last reviewed: 2026-11-09. This is an operational diagnosis and a **non-production release runbook**, not evidence of a published Android app.

## Supported build path: GitHub Actions

Use [Android Shell](../.github/workflows/android-shell.yml) for repeatable, unsigned Android builds. The workflow:
- uses a pinned checkout, Java 17, and Gradle 8.11.1; fails early if Java or Gradle is missing;
- runs signing-input/identity safety regression tests, release lint, application unit tests, and builds a debug APK plus an **unsigned** release AAB;
- uploads build outputs and `SHA256SUMS.txt` for 14 days; and
- does not receive production Stripe keys or Play upload-signing secrets.

To obtain the test build: GitHub > Actions > **Android Shell** > a successful run > **Artifacts** > `wrenchrelay-industrial-android-build`. Check the SHA-256 checksums against the extracted files before distributing them. The debug APK is for testing; the unsigned AAB cannot be published to Play as-is.

The separate [Play internal signing candidate](../.github/workflows/android-play-internal-candidate.yml) requires owner-verified package name, unused versionCode, upload certificate fingerprint, a reviewed full commit SHA, and protected environment secrets. Its checks alone do **not** demonstrate Play Console readiness or publication. See [PLAY_SIGNING_WORKFLOW.md](PLAY_SIGNING_WORKFLOW.md).

## Railway Android builder diagnosis (production environment)

As observed on November 9, 2026:

| Railway service | Observation | Implication |
| --- | --- | --- |
| `wrenchrelay-android-builder` | `mingc/android-build-box:latest`; runtime script from `ANDROID_BUILD_SCRIPT_B64` exits with `/tmp/build.sh: line 347: gradle: command not found`; `/health` never responds | **Failed Android build**; do not infer success from its old online deployment |
| `wrenchrelay-android-builder2` | Android SDK image but starts a small HTTP readiness page; log did not locate a Gradle executable | HTTP success is **not** an APK or AAB build |
| `wrenchrelay-android-ci` | Starts a readiness-only static HTTP server | HTTP success is **not** a tested Android artifact |

The legacy Railway service's uploaded build script and image are not tied to a reviewed Git commit. It also generates a keystore in its container during startup, so the resulting certificate is not established as the registered Play upload certificate. An image tagged `:latest` may change between deployments.

**Do not solve this by changing the healthcheck to `/` or running a placeholder web server.** That would only turn a real build failure into a misleading green status.

### Safe Railway follow-up

1. Keep the customer-serving `wrenchrelay-production`, database, payment/recovery, and voice services **unchanged**.
2. Confirm any automation, callback, domain, or artifact retrieval that still depends on `wrenchrelay-android-builder` before deleting, disabling, or replacing it.
3. Remove `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and unrelated AI/vendor credentials from all **build-only** services. Keep the legitimate payment service's credentials intact. Use Railway's variable deletion controls, not an empty or placeholder secret; verify the variable names are gone. Do not paste real values into chat, GitHub, logs, or screenshots.
4. If any credential value was publicly exposed, rotate/revoke it through its provider, update **only** the authorized consumer and confirm payment webhook delivery before retiring the old value. Rotation is a separate production change.
5. For any necessary Railway-native build, provision a pinned image with Java, Android SDK, and Gradle and build from an immutable repository commit with a verified signing pipeline; do not rely on interactive SSH or an opaque base64 startup script. For now, GitHub Actions is the verified route.
6. After consumers are moved and verified, retire idle builders to reduce compute use. Do not remove build outputs or upload keys until independent backups and Play identity are verified.

## Acceptance criteria

- GitHub workflow reports lint, tests, debug APK, unsigned AAB, checksum generation, and artifact upload successful.
- The artifact SHA-256 values match the downloaded files.
- The Play identity, upload key fingerprint, signing environment approval, live login, microphone, navigation, privacy/account deletion, and real-device checks are separately verified.
- No build-only service retains payment/webhook secrets. Webhook payment fulfillment remains independently verified on the actual production backend.
- No claim of Play release, live payments, or Railway builder repair until there is corresponding independent evidence.

## Rollback

If GitHub build regressions occur, revert only the Android Shell workflow change on its own PR/commit. Do not touch customer deployments, DNS, Stripe configuration, or keystores while troubleshooting build CI.
