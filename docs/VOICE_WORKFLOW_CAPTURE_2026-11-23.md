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
