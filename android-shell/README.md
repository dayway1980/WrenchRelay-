# WrenchRelay Industrial Android client

Default package: com.wrenchrelayllc.industrial. Java namespace and launcher:
com.wrenchrelay.industrial. API 36 target, API 26 minimum.

The existing signing workflow properties playApplicationId and playVersionCode
are validated and honored. The legacy package remains explicitly selectable.
VersionCode 1 is a build default; Play usage and eligibility are not established.

## Native notes and privacy

Select a maintenance textarea in the web workspace, tap Speak note, then review
the recognized text before using it. The Android speech-recognition activity processes
audio through the device provider. This client receives text and has no RECORD_AUDIO
permission. It denies WebView audio capture; realtime WebRTC audio is not offered by
this client. Text input remains available.

Speech cannot populate account/password fields, disconnected fields, another
document, or a different page. Reviewed text is inserted through the native textarea
setter with normal input events. No JavaScript-to-native bridge or account-token
extraction is used. Dictation does not approve or submit maintenance records.

The privacy/account menu contains an in-app client privacy notice, the public policy
and deletion request links, and an About screen with installed package/version.
English and Spanish native resources are independent of web language.

A loading indicator and connection-error retry replace a blank failed page.
Only HTTPS first-party pages stay in the WebView; unsupported schemes are blocked.
File selection is explicit and restricted to a first-party top-level page.
The app has a WR launcher mark, not a certification or performance claim.

## Verification and artifacts

Android Shell CI runs input/signing guards, locale tests, native dictation boundary
tests, lint, JUnit, a debug APK and an unsigned AAB. Google bundletool validates the
real LLC AAB. BUILD_IDENTITY.json records package/version, checkout/head commits,
hashes and debug certificate. The default APK is debug-signed, not signed with the
registered owner upload key. The release AAB is unsigned.

A disposable API 35 emulator installs the exact hashed APK, opens the real public
sign-in screen, checks identity/privacy controls, and confirms speech cannot target
the account form. This is not authenticated maintenance, speech-provider audio,
deletion fulfillment, CMMS integration, or physical-device acceptance.

Play upload remains blocked until the Console app, unused versionCode, registered
upload certificate, private owner key, final privacy/Data safety answers and remaining
runtime acceptance are verified. AI-content reporting applicability and enabled payment
paths require review against the final live service.
No job uploads, signs with an owner key, or publishes to Google Play.
