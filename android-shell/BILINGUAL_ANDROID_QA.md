# Android bilingual upgrade — QA and release acceptance

**Status: review branch only; NOT commissioned or in Google Play.**

## Prior work carried forward
The October Android candidate had native English and Spanish Privacy / account-deletion labels, plus microphone-denial and file-picker messaging. The main-branch debug APK built on November 9, 2026 lacked these native controls. This candidate stages the existing first-party Android improvements from PR #14 onto fresh main without cherry-picking its older workflow history or changing the package or version.

### Native UI and web language
- English default values: `app/src/main/res/values/strings.xml`
- Spanish values: `app/src/main/res/values-es/strings.xml`
- System Spanish locale uses Spanish **native** account, privacy, deletion and permission/fallback labels; system English uses English. Android chooses via normal resource qualifiers.
- The website itself has a different language preference implementation: saved choice > explicit `?lang=` suggestion > browser language > coarse country hint > English. **The native shell must not override the web user's saved choice or request location permission.**
- The inclusion of Spanish native strings is **not proof** that every website, voice prompt, or maintenance workflow is translated.

## Source changes scoped to Android
1. Restore account privacy/deletion control, localized resources and safer first-party URL policy.
2. Restore requested microphone permission handling only for trusted HTTPS and audio resource, with denied-permission text fallback.
3. Restore selected-file chooser and lifecycle cleanup; prohibit backing up WebView/account data.
4. Add pure Java navigation-policy unit tests and stdlib bilingual-resource contract tests to Android Shell workflow.
5. Preserve `applicationId = "com.wrenchrelay.industrial"`, target SDK, versionCode, release signing workflow and existing backend. Do not merge old PR #14 wholesale.

## CI acceptance
- [ ] PR `Android Shell`: Java 17 / Gradle 8.11.1 setup, signing guard self-tests, bilingual XML test, lint, JUnit navigation tests, debug APK, unsigned AAB and checksum artifact all succeed
- [ ] Download new PR artifact and verify hashes; no Play owner key in CI
- [ ] Confirm both Android locales display intended native controls; language switch does not reset web saved choice

## Physical device acceptance, before Play internal submission
- [ ] Install *newly built* debug APK on Android 8+ device; confirm correct package, version and site
- [ ] System English: account, privacy, delete request and fallbacks render English
- [ ] System Spanish: same native controls in Spanish; verify accent rendering, layout clipping, TalkBack labels and back button
- [ ] Change website locale to Spanish, then English; restart shell, verify saved user preference remains prioritized
- [ ] Sign-in/sign-out including external Google OAuth, session persistence and account recovery using synthetic account
- [ ] Confirm native account-deletion control opens real first-party request path; operator processing is separate
- [ ] Verify microphone **allow and deny** branches, typed fallback and privacy indicators; do not claim voice until proven
- [ ] Verify file picker result, cancellation, camera denial, unsafe scheme, nonfirst-party links and network-loss state
- [ ] Review the actual SaaS checkout against Google Play Payments rules before allowing billing in an Android WebView
- [ ] Confirm backend records, CMMS writes, human review, and data privacy separately; none inferred from APK success

## Play identity and signing HOLD
The IdeasApplied Google Play Console browser session on November 10 observed **two different Draft entries**:
`com.wrenchrelay.industrial` and `com.wrenchrelayllc.industrial`. This code builds the first one; do not delete or confuse the second. Neither supplied a registered upload certificate SHA-256 or used track versionCode at that review. Verify App Signing enrollment, owner-upload certificate and unused versionCode, then use owner-approved signing workflow for internal candidate **only**. Never upload unsigned AAB or use the ephemeral Railway keystore. Trader declaration should be reviewed from the account's official dashboard.

No production deploy, payment change, DNS, real customer message, keystore action or Play submission is included.
