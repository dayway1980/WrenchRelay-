import asyncio
from unittest.mock import AsyncMock

import pytest

import fiix_connector
from cmms_voice_draft import VoiceWorkDraft


def approved():
    draft = VoiceWorkDraft("plant-a", "tech-1")
    for key, value in (
        ("asset_id", "P-103"), ("complaint", "Pump stopped"),
        ("actions_taken", "Replaced sensor"),
        ("verification", "Tested normal operation")
    ):
        draft.add_technician_fact(key, value)
    draft.approve(actor_id="tech-1", revision=draft.revision)
    return draft


def test_disabled_by_default():
    with pytest.raises(PermissionError):
        asyncio.run(fiix_connector.write_approved_draft(approved()))


def test_duplicate_claim_never_writes(monkeypatch):
    monkeypatch.setattr(fiix_connector, "claim_idempotency_key",
                        AsyncMock(return_value=({"status": "claimed"}, False)))
    adapter = AsyncMock()
    with pytest.raises(RuntimeError, match="Existing claim"):
        asyncio.run(fiix_connector.write_approved_draft(
            approved(), enabled=True, adapter=adapter))
    adapter.assert_not_awaited()


def test_uncertain_claim_never_retries(monkeypatch):
    monkeypatch.setattr(fiix_connector, "claim_idempotency_key",
                        AsyncMock(return_value=({"status": "uncertain"}, False)))
    adapter = AsyncMock()
    with pytest.raises(fiix_connector.UncertainWriteError):
        asyncio.run(fiix_connector.write_approved_draft(
            approved(), enabled=True, adapter=adapter))
    adapter.assert_not_awaited()


def test_adapter_exception_records_uncertain(monkeypatch):
    monkeypatch.setattr(fiix_connector, "claim_idempotency_key",
                        AsyncMock(return_value=({"status": "claimed"}, True)))
    complete = AsyncMock()
    monkeypatch.setattr(fiix_connector, "complete_idempotency_key", complete)
    adapter = AsyncMock(side_effect=TimeoutError("connection dropped"))
    with pytest.raises(fiix_connector.UncertainWriteError):
        asyncio.run(fiix_connector.write_approved_draft(
            approved(), enabled=True, adapter=adapter))
    assert complete.await_args.kwargs["status"] == "uncertain"
    assert adapter.await_count == 1
