"""Regression: spoken closeout cannot finalize a work order without approval."""
import asyncio
from unittest.mock import AsyncMock

import conversation_router


def test_spoken_closeout_only_proposes(monkeypatch):
    collection = type("Collection", (), {})()
    collection.find_one = AsyncMock(return_value={
        "id": "record-1", "work_order_number": "VR-123", "status": "In Progress"
    })
    collection.update_one = AsyncMock()
    monkeypatch.setattr(conversation_router.db, "work_orders", collection)
    action = asyncio.run(conversation_router.local_action(
        "tenant-a", {"id": "tech-a"},
        "done with VR-123 replaced proximity sensor"
    ))
    assert action["type"] == "closeout_proposal"
    assert action["requires_explicit_approval"] is True
    collection.update_one.assert_not_awaited()


def test_missing_work_order_not_closed(monkeypatch):
    collection = type("Collection", (), {})()
    collection.find_one = AsyncMock(return_value=None)
    collection.update_one = AsyncMock()
    monkeypatch.setattr(conversation_router.db, "work_orders", collection)
    action = asyncio.run(conversation_router.local_action(
        "tenant-a", {"id": "tech-a"},
        "done with VR-123 replaced proximity sensor"
    ))
    assert action is None
    collection.update_one.assert_not_awaited()
