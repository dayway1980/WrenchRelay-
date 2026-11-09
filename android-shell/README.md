# WrenchRelay Android shell

Play-oriented Android wrapper for the first-party WrenchRelay web application.

Identity: `com.wrenchrelay.industrial`
Target SDK: 36
Minimum SDK: 26

Security defaults: HTTPS only, no backup, no file/content access, and non-WrenchRelay links leave the embedded WebView for the system browser. Do not add signing secrets to this repository. Release signing belongs in the protected build/Play pipeline.

Before Play upload: verify the production URL, Google sign-in flow, microphone/voice behavior, privacy/Data Safety declarations, reviewer access, app icon/screenshots, signed AAB, and physical-device QA.

Build or troubleshoot the Android shell via [BUILD_RECOVERY.md](BUILD_RECOVERY.md): use the tested GitHub Actions workflow; the legacy Railway Android builder currently fails before generating a valid artifact. A passing readiness endpoint does not prove an APK or AAB was built.
