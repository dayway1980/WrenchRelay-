# Rivit Continuous Voice — Production Release Contract

Status: implementation required; not approved for production until all gates pass.

## User experience
- On authenticated app entry, greet by preferred name and offer to resume the last authorized unfinished work order. Respect mute/quiet mode and user privacy.
- Request microphone permission through a clear first-run interaction. Once a voice session is started, do not require tap-to-talk for each turn.
- Use bidirectional streaming audio with server-side voice activity detection, interruption/barge-in, natural speech output, explicit listening/thinking/speaking/reconnecting states, and a stop/mute control.
- No browser SpeechSynthesisUtterance as the primary voice experience; it may be an explicitly labeled fallback.
- Use short-lived, server-minted realtime credentials. Never expose a permanent API key to the browser. Authenticate user and authorize workspace on the server.
- On reconnect, preserve session context, do not duplicate utterances or work-order entries. Explain offline/permission failures in plain language.

## Work order integration
- Fetch only work orders authorized for the signed-in tenant and user.
- On entering a work order, load last approved record and draft; ask specifically about unresolved items.
- As technician talks, extract equipment ID, complaint, symptoms, error codes, measurements with units, actions, parts, results, and outstanding questions into an autosaved draft.
- Mark provenance for each fact (spoken, CMMS, manual, inference), timestamps and confidence; never fabricate work, measurements or verification.
- Debounce and version drafts; retry safely with idempotency keys and conflict handling.
- On 'job finished', summarize missing fields, request confirmation and generate a human-reviewable work order.
- Save final/CMMS writes only after explicit technician approval; audit actor, change, time, source and destination. Keep read-only integrations read-only.

## Acceptance gates
1. Verify actual production hostname maps to source repository, commit and deployment.
2. Run automated tests for microphone permissions, denied permission, VAD, interruptions, audio playback, disconnect/reconnect and tenant isolation.
3. Complete authenticated Android Chrome customer journey: sign in -> one-time voice start -> multi-turn conversation without taps -> work order lookup -> draft autosave -> review -> approved final save -> reload and verify persistence.
4. Confirm no raw diagnostics or secrets shown in customer UI, and no cross-tenant history leakage.
5. Run accessibility and quiet-mode tests. Track failures and latency without logging sensitive transcripts by default.
6. Deploy to staging, verify, then promote to production only after gates pass; maintain rollback.

## Release blocker
Current code review found browser speechSynthesis in src/App.js, but the screenshot's live voice page has not been mapped conclusively to this source. Do not deploy a speculative UI replacement.

## User-selectable voice and personality
- Provide separate controls for **voice** (available natural-sounding voice presets, preview, pace) and **personality** (tone and communication style). Changing either must not alter technical accuracy, permissions, safety constraints, or record-approval rules.
- Offer a practical default ("Shop-Floor Friendly") plus Straight Shooter, Calm Expert, Coach, Controls Nerd, Reliability Pro, and other existing personality presets where appropriate. Allow users to switch presets and hear a short preview.
- Persist each authenticated user's selected voice and personality as account preferences, scoped to their identity, and restore them on subsequent sessions and devices. Never infer a user's voice identity from microphone audio.
- Natural greeting uses the user's preferred name and only authorized, saved work history. Avoid repetitive greetings on navigation or reconnect. Do not automatically speak private job details on a shared device before authentication.
- Conversational behavior: concise spoken responses, turn-taking, user interruption, follow-up questions, context continuity, and optional captions/transcript. Never claim to be ChatGPT or impersonate a person.
- Test voice/personality combinations for switching mid-session, persistence after sign-out/sign-in, safe technical answers, mobile playback and accessibility.
