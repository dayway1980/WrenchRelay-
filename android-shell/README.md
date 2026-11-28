# WrenchRelay Android shell

Play-oriented Android wrapper for the first-party WrenchRelay web application.

Identity: `com.wrenchrelay.industrial`
Target SDK: 36
Minimum SDK: 26

Security defaults: HTTPS only, no backup, no file/content access, and non-WrenchRelay links leave the embedded WebView for the system browser. Do not add signing secrets to this repository. Release signing belongs in the protected build/Play pipeline.

Before Play upload: verify the production URL, Google sign-in flow, microphone/voice behavior, privacy/Data Safety declarations, reviewer access, app icon/screenshots, signed AAB, and physical-device QA.

Build or troubleshoot the Android shell via [BUILD_RECOVERY.md](BUILD_RECOVERY.md): use the tested GitHub Actions workflow; the legacy Railway Android builder currently fails before generating a valid artifact. A passing readiness endpoint does not prove an APK or AAB was built.

## English and Spanish — internal QA candidate

The Android shell has localized native strings in `app/src/main/res/values/strings.xml` (English) and `app/src/main/res/values-es/strings.xml` (Spanish). Android chooses these labels from the device locale, including the native Privacy / account-deletion control; changing the device locale must not reset the website's own saved language preference.

The website's prior language policy remains independent of this shell: saved user choice → explicit `?lang=` suggestion → browser language → coarse country hint → English fallback. Do not override a saved preference from Android or require precise device location. The app does not claim that every website screen is translated merely because its native control is localized.

The `Android Shell` GitHub workflow now validates locale-file parity and builds a new debug APK and unsigned AAB on a review branch. See [BILINGUAL_ANDROID_QA.md](BILINGUAL_ANDROID_QA.md) for exact device checks. This does not configure signing or publish a Google Play release. Default CI artifacts retain `com.wrenchrelay.industrial`. The current Play setup priority is the separate `com.wrenchrelayllc.industrial` entry, selected through the explicit build properties below; neither Console draft is changed by CI.

## Explicit Play package and version selection

The existing protected signing workflow passes `playApplicationId` and
`playVersionCode` to Gradle. The app now consumes and validates both properties.
The default development build keeps `com.wrenchrelay.industrial` and versionCode 1;
the separately prioritized Play app is `com.wrenchrelayllc.industrial`.
The Java namespace and launcher class remain `com.wrenchrelay.industrial` for both.

For the LLC package, pass `-PplayApplicationId=com.wrenchrelayllc.industrial` and
`-PplayVersionCode=VERIFIED_UNUSED_VERSION_CODE`. Replace the latter value only after
reading the target app and all used version codes in Play Console. Invalid package
names and out-of-range version codes fail configuration. Defaults do not establish
that version 1 or either package is eligible for an existing Play release.

Android Shell CI builds its existing default debug APK and unsigned AAB, then
checks the LLC package and versionCode 12345 in a regenerated merged manifest.
12345 is only a configuration-test fixture: it is not selected for a Play release
and is never signed or uploaded. The existing default build artifacts are preserved.

This wiring fix does not establish the registered upload certificate, signing-key
availability, current Play release contents, privacy/Data safety accuracy, device QA
or Google authentication. The live Android privacy notice and the reviewed microphone
implementation must be reconciled against the final selected bundle before rollout.
No workflow here uploads to Google Play or publishes a testing/production release.
