# WrenchRelay Android shell

Android WebView wrapper for the first-party WrenchRelay website. This branch improves
microphone and file input handling, external navigation safety, and automated checks.
It has **not** been fully device-commissioned or published.

## Release identity HOLD

Current Android build identity: `com.wrenchrelay.industrial` (versionCode 1, targetSdk 36).
Earlier release records mention `com.wrenchrelayllc.industrial`. A Play Console app ID
is **not** evidence of its package name. Before using any .aab, obtain the existing
package name and versionCode from Play Console > App integrity / release explorer.
If this is a new app, confirm the intended final package name before first upload.
Changing an existing Play package name is not an update; it creates another app.

## Voice and safety

- The WebView asks for the Android microphone permission only when a first-party
  HTTPS page explicitly requests audio capture; other web resources are denied.
- If microphone permission is denied, keep typed notes available. Verify voice
  start/stop, incoming calls, Bluetooth, audio interruption, and on-device privacy.
- External links are browser intents. In particular, Google OAuth generally rejects
  embedded WebViews; **Google sign-in remains a functional test blocker** until a
  proper browser-based authentication/deep-link or verified TWA flow is proven.
- Only HTTPS first-party navigation remains inside the WebView. It does not use
  Android JavaScript bridges or grant camera permissions.
- The host URL currently defaults to https://wrenchrelayllc.com/. Confirm that this
  points to the intended Industrial workflow and that all subsequent flows work.

## In-app privacy and deletion

The Android shell now contains a persistent native "Privacy and account deletion" control above the WebView. It opens first-party HTTPS policy or deletion-request pages in an external browser; no user credentials are embedded in a URL. The deletion page currently initiates an email-based, verified human request, **not automatic erasure**. Play policy compliance still requires operator evidence of the completed deletion process and accurate retention disclosures, and a physical-device check of this control.

## Signing HOLD

GitHub Actions builds a debug APK and an **unsigned** release AAB. Neither
represents an approved production build. Keep Play upload credentials, upload key
and key backup outside GitHub. Use Play App Signing and owner-controlled signing,
then verify package, certificate digest, versionCode, and target API.

## Required commissioning before internal-test rollout

1. Verify live HTTPS DNS/routing, industrial selection, auth, native deletion control and its email request handling,
   privacy-policy URL, support email and accurate Data Safety declarations.
2. Confirm expected package and existing Play versionCode/certificate.
3. Build/review signed AAB with protected upload key; never reuse any other app's key.
4. Run lint and unit tests; physically test a compatible Android device.
5. Test sign-up, login/logout, Google OAuth flow, microphone allow/deny, text fallback,
   attaching a photo/file, incoming-call interruption, offline/online recovery.
6. Complete technician workflows: voice/text evidence, asset ID readback,
   evidence-ranked hypothesis, UNRESOLVED abstention, human-reviewed work order,
   shift handoff, history, export and no automatic safety-critical machinery action.
7. Test backend health, 4xx/5xx/retry behavior, payment sandbox (if exposed),
   privacy/retention, crash reporting and poor network performance.
8. Configure internal testers and test for failures; only then submit Play review.
   Preserve screenshots, test dates, checksums, and rollback/recovery instructions.


## Owner-controlled Play internal signing workflow (no auto-publish)

The manual GitHub Actions workflow `.github/workflows/android-play-internal-candidate.yml`
builds the exact source revision after package identity and versionCode are verified
against **the actual WrenchRelay Industrial Play Console app**. It signs the
Android App Bundle with the **existing** owner-controlled upload certificate,
compares that certificate's SHA-256 fingerprint with the owner's Play Console
App integrity fingerprint, and creates a seven-day signed candidate artifact.
It never uses a debug key or uploads to Play. If inputs/secrets are missing or
the certificate does not match, the workflow fails closed.

**Before pressing Run workflow:**
1. Sign in to the existing IdeasApplied Play Console account. Locate the
   actual WrenchRelay Industrial app; do not infer package identity from a name,
   developer-account link, or draft listing. Read package, highest versionCode,
   upload certificate SHA-256, signing-key status and account verification status.
2. Check whether an existing upload keystore is owner-held or builder-held.
   If the app is already associated with a different upload certificate, follow
   the official Play Console upload-key reset process; never invent or overwrite
   its original keystore. Do not reuse the Android debug key.
3. Create the GitHub repository environment named `play-internal-signing`.
   Put the current upload keystore and credentials in these protected secrets:
   `PLAY_UPLOAD_KEYSTORE_B64` (base64-encoded keystore bytes),
   `PLAY_STORE_PASSWORD`, `PLAY_KEY_PASSWORD`, `PLAY_KEY_ALIAS`.
   Do not put a keystore, private key, tokens or passwords in source, issues,
   chat messages, logs or artifacts. Use environment protection/reviewers if
   available. Do not create a paid plan just for this.
4. GitHub requires a manually dispatched workflow definition to exist on the
   repository's **default branch**. This signing workflow is currently staged
   on PR #14 and is therefore **not yet manually runnable**. Following code
   review, place only the vetted signing workflow on `main` without deploying
   the incompatible application backend. Then choose **Android Play internal
   signing candidate**, select the vetted source branch, click `Run workflow`,
   and supply the verified package
   (one of the two historical candidates), a **new unused** versionCode,
   the public SHA-256 upload certificate fingerprint and the exact operator
   confirmation phrase displayed in the workflow.
5. Inspect the signed artifact, certificate and checksum. After real-device
   tests and store-content compliance checks, upload that artifact to the
   existing app's **Internal testing** track in Play Console. Do not use
   Production, or create another package, without an approved release.
6. If a personal developer account was created after November 13, 2023,
   check whether Google's separate minimum 12 continuously opted-in
   closed testers for 14 days applies before requesting Production access.

**Other mandatory gates:** verify independent Android authentication/
Google sign-in, real-device voice/file picker, working account deletion
operations and Data safety declarations. In particular, a WebView showing
paid SaaS checkout may trigger Google Play's digital-services Payments policy.
Do not enable in-app Stripe checkout or link to outside payment until the
specific Play Billing/eligible alternative-billing policy path is approved.
The disabled current checkout is not evidence of permanent compliance.
Protect and preserve the live Railway SQLite app and Stripe webhook while
testing this separately built MongoDB candidate.

The workflow has no Google Play Publisher service-account access and performs
no upload, submission, production deployment, app-store purchase or charge.
