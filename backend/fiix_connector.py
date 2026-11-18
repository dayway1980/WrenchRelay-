"""Fiix write orchestration; disabled by default.

A validated vendor adapter must be supplied. This module deliberately does not
assume a Fiix URL, authentication scheme or writable field names.
"""
from typing import Any, Awaitable, Callable

from cmms_draft_store import claim_idempotency_key, complete_idempotency_key
from cmms_voice_draft import VoiceWorkDraft


class UncertainWriteError(RuntimeError):
    """External outcome is unknown; reconciliation is mandatory."""


async def write_approved_draft(
    draft: VoiceWorkDraft, *,
    enabled: bool = False,
    adapter: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if not enabled or adapter is None:
        raise PermissionError("Fiix writes are not commissioned")
    payload = draft.connector_payload(
        organization_id=draft.organization_id, actor_id=draft.user_id,
        capability="work_orders:write",
    )
    key = payload["idempotency_key"]
    record, acquired = await claim_idempotency_key(
        draft.organization_id, key, actor_id=draft.user_id,
        draft_id=draft.draft_id, operation=draft.operation,
        payload_summary={"revision": draft.revision},
    )
    if not acquired:
        if record["status"] == "succeeded":
            return record.get("result") or {}
        if record["status"] == "uncertain":
            raise UncertainWriteError("Reconcile the prior Fiix write before retrying")
        raise RuntimeError("Existing claim blocks a second write")

    try:
        result = await adapter(payload)
    except Exception as exc:
        # An adapter exception may occur after Fiix accepted the operation.
        await complete_idempotency_key(
            draft.organization_id, key, status="uncertain",
            result={"message": "Outcome requires reconciliation"},
        )
        raise UncertainWriteError("Fiix outcome unknown; no automatic retry") from exc

    # A persistence failure here must never trigger another external write.
    await complete_idempotency_key(
        draft.organization_id, key, status="succeeded", result=result
    )
    return result
