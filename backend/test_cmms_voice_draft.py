import pytest

from cmms_voice_draft import VoiceWorkDraft


def completed_draft():
    draft = VoiceWorkDraft("plant-a", "tech-1")
    for key, value in (
        ("asset_id", "P-103"),
        ("complaint", "Pump stopped"),
        ("actions_taken", "Replaced sensor"),
        ("verification", "Tested normal operation"),
    ):
        draft.add_technician_fact(key, value)
    return draft


def test_requires_approval_and_capability():
    draft = completed_draft()
    with pytest.raises(PermissionError):
        draft.connector_payload(organization_id="plant-a", actor_id="tech-1",
                                capability="work_orders:write")
    draft.approve(actor_id="tech-1", revision=draft.revision)
    assert draft.connector_payload(organization_id="plant-a", actor_id="tech-1",
                                   capability="work_orders:write")["fields"]["asset_id"] == "P-103"
    with pytest.raises(PermissionError):
        draft.connector_payload(organization_id="plant-a", actor_id="tech-1",
                                capability="work_orders:read")


def test_prevents_cross_tenant_and_user_writes():
    draft = completed_draft()
    with pytest.raises(PermissionError):
        draft.approve(actor_id="another-tech", revision=draft.revision)
    draft.approve(actor_id="tech-1", revision=draft.revision)
    with pytest.raises(PermissionError):
        draft.connector_payload(organization_id="plant-b", actor_id="tech-1",
                                capability="work_orders:write")


def test_edits_invalidate_approval():
    draft = completed_draft()
    draft.approve(actor_id="tech-1", revision=draft.revision)
    draft.add_technician_fact("parts_used", "Proximity sensor")
    with pytest.raises(PermissionError):
        draft.connector_payload(organization_id="plant-a", actor_id="tech-1",
                                capability="work_orders:write")


def test_missing_facts_cannot_be_approved():
    draft = VoiceWorkDraft("plant-a", "tech-1")
    draft.add_technician_fact("complaint", "No start")
    with pytest.raises(ValueError):
        draft.approve(actor_id="tech-1", revision=draft.revision)
