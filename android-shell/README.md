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

The `Android Shell` GitHub workflow now validates locale-file parity and builds a new debug APK and unsigned AAB on a review branch. See [BILINGUAL_ANDROID_QA.md](BILINGUAL_ANDROID_QA.md) for exact device checks. This does not configure signing or publish a Google Play release. The intended internal-test draft is the existing `com.wrenchrelay.industrial` entry; the separate `com.wrenchrelayllc.industrial` draft remains unchanged.
