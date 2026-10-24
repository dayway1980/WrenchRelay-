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

## Signing HOLD

GitHub Actions builds a debug APK and an **unsigned** release AAB. Neither
represents an approved production build. Keep Play upload credentials, upload key
and key backup outside GitHub. Use Play App Signing and owner-controlled signing,
then verify package, certificate digest, versionCode, and target API.

## Required commissioning before internal-test rollout

1. Verify live HTTPS DNS/routing, industrial selection, auth, account deletion,
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
