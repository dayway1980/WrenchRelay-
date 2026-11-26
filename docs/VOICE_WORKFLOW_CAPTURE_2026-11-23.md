# WrenchRelay Repair Workflow Capture — staged prototype (2026-11-23)

## Purpose and product boundary
Inspired by the **general, publicly described** workflow pattern of capture → editable steps → review → export, build a WrenchRelay-specific, original tool for Industrial and Automotive technicians. Do not copy Scribe's code, screenshots, branded assets, wording, proprietary interface, or extensions.

WrenchRelay's differentiation is **evidence and repair outcomes**: a technician should document the reported problem, observations, tests, safety and energy controls, actual actions or parts, and verification. Do not present hypothetical fixes or missing facts as verified.

## Implemented in this branch
- New **Capture steps** navigation item in the authenticated WrenchRelay React app's Industrial and Automotive modes (`web/src/App.js`).
- Explicit Start / Stop capture. User-triggered browser speech recognition for **one dictated entry at a time** or type and edit manually.
- Concise spoken follow-up questions from a **deterministic, user-visible checklist**, rather than implying the browser speech engine is ChatGPT. Speech output can be disabled.
- Step category editing, transcript correction, deletion, a read-only draft and missing-evidence questions. A microphone may require browser permission. Mobile browsers without speech support retain full typed functionality.
- Non-approved, clearly labelled workflow draft exported as `.txt` or moved into the existing work-order editor **only after explicit technician review checkbox**. No click auto-saves, inserts a CMMS work order, sends outreach, publishes a procedure, or changes equipment.
- Explicit disclosure: no screen recording, background microphone, or uploads by this component. Depending on browser, opt-in speech-to-text may be processed by the browser's speech vendor.
- Correct an unrelated historical legal-entity reference in the `web/` frontend to WrenchRelay LLC.

## Known limitations / NOT YET COMMISSIONED
- This is an original guided voice-assisted workflow capture **MVP**, not a clone of Scribe's extension or auto-screenshot technology.
- Voice uses browser SpeechRecognition and speechSynthesis; it is **NOT OpenAI Realtime or ChatGPT Voice**, does not support full-duplex interaction or true interruption-aware model turns. The existing app can generate AI work-order drafts only after user review via its existing AI backend.
- Notes exist in React session memory until the technician explicitly exports, moves to editor, or leaves the screen. This is not evidence of durable cloud persistence or synced mobile support.
- No medical/financial data should be dictated. For shop/plant workflows, do not enter proprietary plant information or personal customer details without authorization.
- No photograph, CCTV, clickstream, general desktop capture, or external automation has been implemented.
- The stand-alone Automotive missed-call shop portal is a **separate application**; this change does not modify its customers, authentication, or checkout.
- The **live Railway backend** is assembled from archived source with SQLite and may diverge from GitHub source. Vercel `READY` preview builds and GitHub unit tests are not proof of Railway production deployment.

## Next stage: OpenAI realtime voice agent
Before enabling an actual low-latency, interruptible ChatGPT-style voice interface:
1. Resolve the exact deployed customer app and backend, then add an authenticated, rate-limited backend endpoint that mints a **short-lived ephemeral Realtime client secret**. Never publish a permanent OpenAI key in frontend JS.
2. Configure WebRTC browser audio and server-approved realtime model/voice, explicit mic consent, browser permission and stop/mute, with full-duplex interruptions tested. Validate OpenAI pricing, API credit limits and failure handling.
3. Use a server-controlled WrenchRelay prompt that asks one missing-evidence question at a time, distinguishes observations/hypotheses/verified outcomes, preserves units, and refuses to bypass safety systems.
4. Record **editable transcripts with consent** and trace provenance per technician. Avoid retaining raw recordings by default. Require redaction and explicit approval before any knowledge-sharing or public page.
5. Recheck organization/asset access, data boundaries, usage quotas, and CMMS writes (approval-gated) in each tool, never in the voice model alone.
6. Test noisy industrial environments, multiple speakers, Spanish/English terms, interruptions, hallucinated torque/electrical values, outage/reconnection and account isolation in a private staging environment before production rollout.

Official architecture reference: https://developers.openai.com/api/docs/guides/realtime

## Checks
- GitHub Actions job `Voice workflow capture checks` runs `node --check web/src/workflowCapture.mjs` and `node --test web/src/workflowCapture.test.mjs`.
- Build the preview and do an authenticated manual flow for **both** Industrial and Automotive: start/stop, typed fallback, permission denial, speech review, edit/remove, incomplete steps, Spanish prompts, export, move to work-order editor; verify no unapproved CMMS changes or sign-ups.
- Do not merge/deploy this branch to live Railway until live source and DB preservation are verified. Keep billing commissioning PR #51 separate and draft.


## Follow-on implementation — Realtime voice bridge (Nov 23, 2026)
A further code-only milestone is now staged **on this same feature branch**:

- `api-service/realtime_voice.py` adds `POST /api/realtime/client-secret`, using the existing authenticated `current_user` dependency, user document and MongoDB quota counter. No API key is sent to the frontend.
- A valid browser Origin must match an explicit allowlist. Two server variables are required together: `WRENCHRELAY_REALTIME_ENABLED=true` AND `WRENCHRELAY_REALTIME_BUDGET_APPROVED=true`. Both default off. An `OPENAI_API_KEY` must be present on the **correct isolated** backend.
- Each credential expires 60 seconds after creation and permits session creation while valid. Daily issuance is provisionally limited to two requests per account via an atomic DB update; provider failures refund the quota.
- The GA Realtime session uses `gpt-realtime-2.1`, voice `marin`, server VAD, input transcription with `gpt-transcribe`, and **no model tools or CMMS writes**. The model must ask one question at a time and preserve unknown evidence.
- `web/src/RealtimeVoice.js` implements an optional authenticated WebRTC client with an explicit audio consent checkbox, user-initiated microphone, a visible stop/mute control, no automatic microphone recording by WrenchRelay, local assistant transcript output and technician-review handoff. The browser stops its own connection after 180 seconds. Only editable captured text may be passed into the existing work-order flow by a user.
- The `web/src/WorkflowCapture.js` interface only renders this component when `/api/config` explicitly advertises `realtime_voice_enabled`. Regular step capture remains available without the feature.

**NO COST GUARANTEE:** short-lived secrets may be used for more than one session during their validity and a client timer can be bypassed. The two-token limit is NOT a provider-enforced duration or dollar cap. The API organization/project must have independently verified spending protections and server-side monitoring or session enforcement before approving the budget flag.

**NO PRODUCTION COMMISSIONING YET:** The Railway application customers currently access uses an archived SQLite runtime, not this repository's MongoDB-based `api-service/main.py`. Additionally, the connected Vercel `wrench-relay` project exposes the **same sensitive DB variables to production and preview**. Do not point a preview test at the real customer database. A separate dummy-data database/project and an explicitly provisioned trial OpenAI project are prerequisites for real microphone/audio E2E testing. Never change the live DNS, existing accounts, Stripe, or the Railway backend to enable a speculative preview.

### Verified automated checks
`python -m unittest discover -s api-service -p 'test_realtime_voice.py' -v` checks:
- closed flag, authentication and origin enforcement
- safe test-only token issuance, no persistent-key disclosure, session model and tool-disable contract
- atomic per-user token allowance
- provider error handling and quota refund
- invalid mode/language requests

`node --test web/src/workflowCapture.test.mjs` checks the maintenance evidence model. GitHub Actions runs both. Vercel READY is a frontend build result, not a live audio E2E test.

### Additional release checks required
1. Restore production **SQLite** to an isolated test environment and verify existing customer login and work order contents remain intact. Do not use the Vercel shared production MongoDB for testing.
2. Confirm which current backend serves the customer account entry point and where `/api/config` requests route.
3. Establish a safe, monitored standalone Realtime backend that can authenticate customer sessions **against the actual production auth system without copying credentials or leaking customer data**. The current MongoDB-based bridge is a reference implementation, not proof of Railway compatibility.
4. Use an OpenAI test key/project with explicit dollar alerts/limits and secure secrets; no billable tests until the user authorizes charges and billing.
5. Manual mobile/desktop permission denial, spoken interruption, 180-second expiry, termination, mute, account isolation, transcription accuracy, English/Spanish terminology, and person-to-person takeover.
6. Validate consent wording and privacy retention; only with explicit approval perform a staged canary release and rollback.


## Public isolated sandbox unblocked — November 23, 2026

**Working customer-accessible demonstration (no signup):**
https://wrenchrelay-access-probe.vercel.app/try-workflow

- Deployed from this feature branch to existing Vercel project `wrenchrelay-access-probe` (`prj_VWLJryohpmZD6hxMRoSugddPRvjn`), without creating a new project.
- Its Vercel environment had **zero** variables before deployment. The only added variable is `REACT_APP_PUBLIC_DEMO_ONLY=true`, scoped to this project's production target, which forces the React interface into the offline, browser-only demonstration on all routes.
- Live HTTP extraction independently confirmed the workflow screen renders without Vercel sign-in, includes Industrial/Automotive selector, evidence sections, export/review features and prominent disclaimers. `/login` also renders the demo rather than customer login. This is only an accessibility/render check; interactive microphone permissions and actual edits have **not** been end-to-end browser-tested.
- Vercel deployment `dpl_6dKGBzbVAV29qEPiuANwu3jH7NCT` was **READY**, with the alias `wrenchrelay-access-probe.vercel.app`. No production app custom domains, live Railway services, CNAME, Stripe account or user records changed.
- All four GitHub checks for commit `60781592a2e00f994f086f4c899a3bf1939de92a` passed: voice workflow checks, candidate API config, synthetic auth/billing, and the repeated voice check. This is not proof of an OpenAI-powered live call.
- The demo's voice input uses explicit opt-in browser speech recognition if available. Real AI Realtime remains hidden/disabled on this sandbox. Never describe it as a live AI telephone call or a fully commissioned user app.

**Remaining real Realtime blockers:**
- Vercel's connected account has permission to deploy into the existing isolated project but was denied permission (403) to create a new project. Its AI Gateway budget READ call was denied (403), so account budget setup and verification remain incomplete. Do not claim a spend cap exists.
- Started the user-facing OpenAI Platform secure API key setup for a dedicated `WrenchRelay Voice Sandbox` key; no new permanent key was read or installed by the assistant. The API Platform now supports project hard spend caps, but the project owner must verify and enable **Enforce a hard limit** separately before real billable calls.
- Current code relies on direct OpenAI Realtime, so a Vercel AI Gateway limit would not protect those calls unless the integration is explicitly migrated to the gateway and tested.
- The existing Railway customer runtime uses SQLite and a sealed source archive, and the separate legacy voice candidate has its own unknown authentication/data coupling; neither was overwritten.
- Real OpenAI microphone-to-voice conversation, authenticated customer session equivalence, project-specific cost accounting and cancellation are **NOT TESTED / NOT COMMISSIONED**.

**Smallest remaining reversible action:** Finish owner-side creation of a dedicated restricted OpenAI project/key with a low hard spend limit; provide the key ONLY through Vercel/Railway secret configuration (never in chat). After independently verifying the project budget and test-only auth, test one short real voice session in isolated staging, inspect cost and logs, and stop before any customer-domain cutover.
