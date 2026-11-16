# IdeasApplied shared voice (candidate)

A standalone Cloudflare Worker for authenticated dictation across applications.

- POST /api/voice/transcribe accepts audio bytes with a trusted bearer token.
- POST /api/voice/token fails closed until provider-specific ephemeral token
  issuance and per-app entitlements are implemented.
- No cross-app authentication federation is assumed.
- The initial identity verifier points to WrenchRelay's /api/me endpoint;
  verify the actual deployed identity service and bearer token format.
- Configure VOICE_ALLOWED_ORIGINS before browser use.
- Never transmit or persist transcripts across tenants without permission.
- Audio MIME/container support and actual latency require a live test.
- Do not connect this Worker to public production traffic until verified.

Deployment requires a Cloudflare account with Workers AI binding enabled.
