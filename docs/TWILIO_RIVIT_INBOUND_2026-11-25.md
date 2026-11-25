# Rivit inbound telephone path — wiring and release gates (2026-11-25)

## Why this exists

Before this change the repository contained **no Twilio code of any kind**: no
TwiML endpoint, no `X-Twilio-Signature` validation, no inbound call handler, no
dialed-number-to-tenant mapping and no caller intake store. An inbound call to a
WrenchRelay number therefore had nothing to reach. Whatever answered it, it was
not Rivit.

This branch adds the telephone entry point and the media bridge behind it, and
nothing else. It does not purchase, release or reassign a number, does not place
calls, does not change customer routing and does not enable paid audio.

## What is implemented

`api-service/twilio_voice.py`

| Endpoint | Purpose | Authentication |
| --- | --- | --- |
| `POST /api/voice/incoming` | Twilio voice webhook: answers the call with TwiML | `X-Twilio-Signature` |
| `POST /api/voice/status` | Call lifecycle callbacks, stored durably | `X-Twilio-Signature` |
| `POST /api/voice/intake` | External writer for a structured intake | `X-Rivit-Bridge-Key` |
| `GET /api/voice/intakes` | Shop operator reads their own shop's intakes | Signed-in session + tenant membership |
| `GET /api/voice/calls` | Shop operator reads their own shop's call log | Signed-in session + tenant membership |
| `GET /api/voice/health` | Non-secret readiness report | none (booleans only) |

`api-service/rivit_media_bridge.py`

| Endpoint | Purpose | Authentication |
| --- | --- | --- |
| `WS /api/voice/stream` | Twilio Media Streams <-> OpenAI Realtime relay | Live-approval flag + per-call HMAC token |

Guarantees enforced in code:

1. **Signature first.** Every webhook is verified before anything else happens.
   Missing credentials means HTTP 503, never "trust it anyway".
2. **Exact shop greeting.** The greeting is spoken by Twilio from configuration,
   so the wording is fixed even if a model misbehaves. `&` is escaped, so
   "Griffin Muffler & Brake Center" produces valid TwiML.
3. **Unknown number, no AI.** A call to a number that is not mapped to a tenant
   gets a short refusal and a hangup. No model, no transcript, no intake.
4. **No invented shop facts.** Tenant configuration *rejects* `hours`, `services`,
   `prices`, `availability` and `appointments` keys, and the intake validator
   *rejects* `price`, `quote`, `estimate`, `hours`, `availability`,
   `appointment`, `appointment_confirmed`, `diagnosis` and `repair_completed`.
   The assistant cannot state or promise what the shop has not published, because
   there is nowhere to put it. The model's `record_intake` tool accepts exactly
   the same allow-list.
5. **Replay safe.** Each `(CallSid, stage)` and each `(CallSid, CallStatus)` is
   claimed once through a unique `_id`, so a Twilio retry cannot double-write.
   A duplicate delivery returns byte-identical TwiML.
6. **Tenant isolation.** An operator of shop A gets HTTP 403 for shop B, and an
   unauthenticated read gets HTTP 401. Intake responses are `no-store`.
7. **Live audio is triple-gated.** `<Connect><Stream>` is emitted only when
   `WRENCHRELAY_VOICE_LIVE_APPROVED=true`, `WRENCHRELAY_VOICE_STREAM_URL` is a
   `wss://` URL **and** a bridge key exists to mint the per-call token. The
   socket itself then re-checks the flag, the token, the tenant, the call
   identity and the OpenAI credential, and closes with code 1008 otherwise.
8. **No recording by the application.** This code never emits `<Record>` and
   never dials a transfer. Consent wording is disclosed before the stream only
   when the tenant sets `"recording": "disclosure"`.
9. **The stream carries no reusable secret.** Twilio does not sign WebSocket
   upgrades, so the media URL carries `HMAC-SHA256(bridge key, CallSid)`. It is
   valid for that call only, and the bridge key itself never appears in TwiML,
   logs or a response.
10. **Audio is relayed, not stored.** Payloads pass through untouched in both
    directions; the only data written is the structured intake the caller
    supplied.

## Media bridge behaviour

Twilio sends 8 kHz G.711 mu-law as base64. The Realtime session is configured for
`audio/pcmu`, the GA name for the same codec, so no transcoding happens anywhere.

| Direction | Twilio frame | Realtime event |
| --- | --- | --- |
| Caller -> model | `media.payload` (track `inbound`) | `input_audio_buffer.append` |
| Model -> caller | `media` on the call's `streamSid` | `response.output_audio.delta` |
| Barge-in | `clear` on the call's `streamSid` | `input_audio_buffer.speech_started` |
| Intake | `conversation.item.create` (`function_call_output`) + `response.create` | `response.function_call_arguments.done` |

The model is told the caller already heard the greeting, to ask one question at a
time, and to refuse hours, prices, availability, diagnosis and appointments. Its
only tool is `record_intake`, whose result is stored through the same validator
the HTTP intake endpoint uses. A tool call containing an invented field is
refused, nothing is written, and the model is told it was not recorded.

## Configuration

```bash
# Twilio webhook authentication. Prefer the Auth Token (Twilio's default SHA1
# scheme), or an operator-managed shared key from Twilio's Webhooks
# configuration API (HMAC-SHA256/SHA1).
TWILIO_AUTH_TOKEN=
TWILIO_WEBHOOK_SHARED_KEY=
TWILIO_WEBHOOK_SIGNATURE_ALGORITHM=sha256

# Exact public origin Twilio signs. Required behind Railway/Cloudflare, because
# the internal request URL is http://host:port and will never match.
TWILIO_PUBLIC_BASE_URL=https://api.wrenchrelayllc.com

# Inbound answering and paid audio are separate decisions.
WRENCHRELAY_VOICE_INBOUND_ENABLED=false
WRENCHRELAY_VOICE_LIVE_APPROVED=false
WRENCHRELAY_VOICE_STREAM_URL=

# Bridge between the media stream and the intake store. The same value signs each
# call's stream token and authenticates external intake writers.
WRENCHRELAY_VOICE_BRIDGE_KEY=

# Realtime model settings. Defaults: gpt-realtime / marin.
WRENCHRELAY_VOICE_MODEL=
WRENCHRELAY_VOICE_NAME=

# Server-side credential for the media bridge. Never sent to a browser.
OPENAI_API_KEY=

# Dialed number -> tenant allow-list as JSON.
WRENCHRELAY_VOICE_TENANTS={"+15555550100":{"tenant_id":"griffin-muffler","shop_name":"Griffin Muffler & Brake Center","greeting":"Hi, I'm Rivit. You've reached Griffin Muffler & Brake Center. How can I help you today?","operator_emails":["owner@example.com"],"recording":"none"}}
```

## Wiring a number (operator step, requires approval)

1. Deploy this branch to the **isolated QA** service only.
2. Confirm `GET /api/voice/health` reports `inbound_enabled: true`,
   `signature_auth_configured: true`, `tenants_valid: true`.
3. On the test number, set **Voice: A call comes in** to
   `POST https://<qa-host>/api/voice/incoming`, and **Call status changes** to
   `POST https://<qa-host>/api/voice/status`.
4. With `WRENCHRELAY_VOICE_LIVE_APPROVED=false`, place one authorized test call.
   The call should answer, speak the greeting, say the assistant is still being
   tested, and hang up. Nothing should reach OpenAI.
5. Only after the OpenAI spend cap is confirmed: set
   `WRENCHRELAY_VOICE_STREAM_URL=wss://<qa-host>/api/voice/stream`, then set
   `WRENCHRELAY_VOICE_LIVE_APPROVED=true`. Re-check `/api/voice/health` for
   `stream_configured: true` and `media_bridge_configured: true`.
6. Place one authorized test call and confirm the intake appears for the shop
   operator. Revert step 5 for any doubt; the call falls straight back to hold.

Rollback is two fields: the live flag back to `false`, and the number's voice
webhook back to its previous value. No data migration, no schema change, no DNS
change.

## Known blockers (not resolvable from source alone)

- **The Twilio connector is not available in this workspace.** No Twilio account,
  key or number can be read here, so no live account claim is made in this branch.
- **A Twilio API Key secret cannot validate a webhook signature.** Twilio signs
  with the account Auth Token (HMAC-SHA1) or an explicitly configured shared key.
  The webhook path therefore needs `TWILIO_AUTH_TOKEN` or a shared key; an `SK...`
  key plus its secret is not a substitute.
- **The OpenAI account is unverified from here.** The model name, voice, available
  quota and any dollar spend cap must be confirmed in the account before the live
  flag is raised, or a call will connect and then fail closed with no assistant.
- **Carrier-level recording overrides the application.** If call recording is
  enabled on the number in the Twilio console, Twilio records regardless of what
  this code emits. Recording, consent wording and retention must be decided at
  the account and number level before any customer call.
