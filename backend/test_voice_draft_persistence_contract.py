"""Fast, database-free contract tests for the persistent voice draft model."""
from cmms_voice_draft import VoiceWorkDraft
from cmms_draft_store import _serialize, _deserialize


def draft_ready():
    d = VoiceWorkDraft("plant-a", "tech-a")
    for k, v in (
        ("asset_id", "P-103"), ("complaint", "No start"),
        ("actions_taken", "Replaced proximity sensor"),
        ("verification", "Observed normal operation"),
    ):
        d.add_technician_fact(k, v)
    return d


def test_approval_key_stable_across_repeat_approval_and_reload():
    d = draft_ready()
    d.approve(actor_id="tech-a", revision=d.revision)
    key = d.idempotency_key
    d.approve(actor_id="tech-a", revision=d.revision)
    assert d.idempotency_key == key
    restored = _deserialize(_serialize(d))
    assert restored.idempotency_key == key
    assert restored.draft_id == d.draft_id
    assert restored.connector_payload(
        organization_id="plant-a", actor_id="tech-a",
        capability="work_orders:write",
    )["idempotency_key"] == key


def test_edit_invalidates_approval_and_rotates_key():
    d = draft_ready()
    d.approve(actor_id="tech-a", revision=d.revision)
    old = d.idempotency_key
    d.add_technician_fact("parts_used", "Proximity sensor")
    assert d.idempotency_key is None
    assert d.approved_revision is None
    d.approve(actor_id="tech-a", revision=d.revision)
    assert d.idempotency_key != old
