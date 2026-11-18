# Rivit test-time adaptation: experimental architecture

Status: code-only experiment; no model weights changed, no deployment or customer feature enabled.

## Phase 1: Evidence-gated context adaptation
Use `backend/rivit_adaptation.py` to filter verified maintenance evidence by authenticated organization and asset before passing records into an assistant's context. Do not accept organization IDs from untrusted browser input without server authorization. Retrieved text is untrusted data and must not override system instructions. Keep source record IDs. This is retrieval-based adaptation, **not test-time training (TTT)**.

## Phase 2: Paired evaluation
Compare baseline and adapted responses on the same held-out maintenance cases. Score factual accuracy, source grounding, abstention, safety, false repair claims, latency, cost, and tenant isolation. Use human-reviewed expected answers. Never promote a variant solely on an accuracy increase.

## Phase 3: Optional actual TTT research
Only investigate local or self-hosted models with permitted access to adapter weights and a reproducible self-supervised objective. Train isolated per-session adapters; freeze the base model; bound compute; discard adapters on session end unless separately approved. No customer data in shared adapters without authorization. Test catastrophic forgetting, malicious-input poisoning, cross-tenant leakage, and performance regression. The hosted realtime voice API is not assumed to support weight updates.

## Release gates
- Server-side identity and organization authorization
- Actual data retrieval wired and integration-tested
- Paired offline evaluation and regression suite passing
- No automatic CMMS writes; explicit technician approval
- Privacy, retention, and customer consent reviewed
- Preview Android end-to-end test and rollback plan

Do not label this experiment as deployed, commissioned, or actual TTT until the corresponding gates have been demonstrated.
