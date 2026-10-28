# WrenchRelay Industrial — proposed Google Play listing and release evidence

Status: **DRAFT FOR INTERNAL TESTING**. This text is not proof of current functionality,
customer acceptance, a signed release, or approval by Google Play.

## Proposed store listing
- App title (≤30 characters): **WrenchRelay Industrial**
- Category: Business
- Short description (≤80 characters):
  **Capture maintenance notes, draft work orders, and review shift handoffs.**
- Operator: WrenchRelay LLC
- Support: support@wrenchrelay.app (verify inbox ownership and delivery before public release)
- Privacy policy: https://wrenchrelayllc.com/privacy
- External account deletion request: https://wrenchrelayllc.com/delete-account

### Proposed long description

WrenchRelay Industrial is a maintenance documentation and workflow tool designed for
technicians working with industrial equipment.

Record equipment details, symptoms, observations and previous actions. Organize
information for work-order drafts, troubleshooting notes and shift handoffs. Review
AI-assisted suggestions before using them in maintenance records.

WrenchRelay is a documentation assistant, not a substitute for qualified personnel,
lockout/tagout procedures, equipment manuals or independent verification. It does
not operate industrial machinery.

Feature availability depends on your organization's configured account, service
connectivity and product plan. Some functions may be unavailable during testing.

## Release claims that require device evidence
- App installation/first launch on representative Android device
- Correct Industrial experience at https://wrenchrelayllc.com/
- Actual registration, login/logout, account recovery and external browser sign-in
- Microphone permission allow/deny, recording, interruption, and typed-note fallback
- File picker, photos/files (if enabled), and network recovery
- Review/edit/approve work orders, handoffs, export and tenant isolation
- In-app privacy and deletion request; verified back-office deletion completion
- Correct disclosures for any analytics, crash logs, uploads or AI processing

Do not mark an untested function as fully available in the public listing.

## Play Console release blockers (complete in actual console)
- Verify the **existing Play app package**; candidates in source/history disagree:
  com.wrenchrelay.industrial vs com.wrenchrelayllc.industrial.
- Read current highest versionCode, Google Play App Signing status, and upload
  certificate SHA-256 fingerprint. Preserve the preexisting certificate.
- Confirm developer identity and specific package registration status.
  July 18 Play email confirmed automatic registration of *eligible existing apps*
  under IdeasApplied, not the identity of WrenchRelay Industrial.
- Sign with owner-managed existing upload key; release a new version to **Internal
  testing** first. The CI unsigned .aab is NOT an upload candidate.
- Supply accurate Data safety categories after inspecting the backend's real
  data path: account email, maintenance notes, attachments/recordings, session
  identifiers, security logs, any payment metadata, AI service routing and
  retention. Never fill this section with unsupported "no data collected" claims.
- Provide complete public privacy-policy disclosures; the current short page
  must be audited for completeness before public distribution.
- Test account deletion from the app and external link. An email request page is
  only the beginning; an accountable operator must actually process requests.
- Confirm content rating, target audience, support email, store graphics, real
  on-device screenshots, login credentials for reviewers and financial features.
- Review Google Play Payments policy. Paid SaaS checkout inside a WebView may
  require Play Billing or an approved regional alternative payment program;
  do not enable the existing Stripe CTA by default.
- If the developer account is a **personal** account opened after Nov 13, 2023,
  check Play's 12 continuous closed testers / 14-day production-access rule.

## Evidence and approval
- Signed candidate workflow: .github/workflows/android-play-internal-candidate.yml
- Input checker: android-shell/verify_play_release.py
- Android source PR: https://github.com/dayway1980/WrenchRelay-/pull/14
- Repo security PR: https://github.com/dayway1980/WrenchRelay-/pull/24
- Production Railway service is a separate SQLite archive; the GitHub web app
  is MongoDB-based. **Do not replace it merely because APK CI is green.**

No production Play submission, DNS change, customer data migration or charge
is authorized by this draft. Store publication and billing require verified
app-specific evidence and an approved rollout decision.
