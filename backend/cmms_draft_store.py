"""Persistent voice drafts and single-writer CMMS write claims.

A claimed or uncertain operation must be reconciled with the CMMS before retry.
The claim collection requires its unique index before any connector is enabled.
"""
from typing import Any

from pymongo.errors import DuplicateKeyError

from cmms_voice_draft import VoiceWorkDraft
from db import db, now_iso


def _serialize(draft: VoiceWorkDraft) -> dict[str, Any]:
    return {
        "draft_id": draft.draft_id, "organization_id": draft.organization_id,
        "user_id": draft.user_id, "operation": draft.operation,
        "fields": dict(draft.fields), "provenance": dict(draft.provenance),
        "revision": draft.revision, "approved_revision": draft.approved_revision,
        "idempotency_key": draft.idempotency_key, "updated_at": now_iso(),
    }


def _deserialize(doc: dict[str, Any]) -> VoiceWorkDraft:
    draft = VoiceWorkDraft(
        organization_id=doc["organization_id"], user_id=doc["user_id"],
        draft_id=doc["draft_id"], operation=doc.get("operation", "closeout")
    )
    draft.fields = dict(doc.get("fields") or {})
    draft.provenance = dict(doc.get("provenance") or {})
    draft.revision = int(doc.get("revision", 0))
    draft.approved_revision = doc.get("approved_revision")
    draft.idempotency_key = doc.get("idempotency_key")
    return draft


async def save_draft(draft: VoiceWorkDraft) -> None:
    doc = _serialize(draft)
    await db.voice_drafts.update_one(
        {"organization_id": draft.organization_id, "draft_id": draft.draft_id},
        {"$set": doc, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )


async def load_draft(organization_id: str, draft_id: str) -> VoiceWorkDraft | None:
    doc = await db.voice_drafts.find_one(
        {"organization_id": organization_id, "draft_id": draft_id}, {"_id": 0}
    )
    return _deserialize(doc) if doc else None


async def load_latest_draft_for_user(
    organization_id: str, user_id: str
) -> VoiceWorkDraft | None:
    doc = await db.voice_drafts.find_one(
        {"organization_id": organization_id, "user_id": user_id},
        {"_id": 0}, sort=[("updated_at", -1)]
    )
    return _deserialize(doc) if doc else None


async def claim_idempotency_key(
    organization_id: str, idempotency_key: str, *,
    actor_id: str, draft_id: str, operation: str,
    payload_summary: dict[str, Any] | None = None
) -> tuple[dict[str, Any], bool]:
    """Returns (record, acquired). Only acquired=True may start an external write."""
    if not idempotency_key:
        raise ValueError("Idempotency key required")
    record = {
        "organization_id": organization_id, "idempotency_key": idempotency_key,
        "actor_id": actor_id, "draft_id": draft_id, "operation": operation,
        "status": "claimed", "payload_summary": payload_summary or {},
        "result": None, "claimed_at": now_iso(), "completed_at": None,
    }
    try:
        await db.cmms_idempotency_keys.insert_one(dict(record))
        return record, True
    except DuplicateKeyError:
        existing = await db.cmms_idempotency_keys.find_one(
            {"organization_id": organization_id, "idempotency_key": idempotency_key},
            {"_id": 0}
        )
        if existing is None:
            raise
        if (existing["actor_id"], existing["draft_id"], existing["operation"]) != (
            actor_id, draft_id, operation
        ):
            raise PermissionError("Idempotency key reused for another operation")
        return existing, False


async def complete_idempotency_key(
    organization_id: str, idempotency_key: str, *,
    status: str, result: dict[str, Any] | None = None
) -> None:
    if status not in ("succeeded", "failed", "uncertain"):
        raise ValueError("Unsupported idempotency status")
    outcome = await db.cmms_idempotency_keys.update_one(
        {"organization_id": organization_id, "idempotency_key": idempotency_key,
         "status": "claimed"},
        {"$set": {"status": status, "result": result, "completed_at": now_iso()}}
    )
    if outcome.matched_count != 1:
        raise ValueError("Claim missing or already finalized")


async def get_idempotency_record(
    organization_id: str, idempotency_key: str
) -> dict[str, Any] | None:
    return await db.cmms_idempotency_keys.find_one(
        {"organization_id": organization_id, "idempotency_key": idempotency_key},
        {"_id": 0}
    )
