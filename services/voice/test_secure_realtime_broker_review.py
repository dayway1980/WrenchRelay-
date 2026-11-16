"""Fail-closed quota and identity contract checks (synthetic)."""
import asyncio
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from services.voice.secure_realtime_broker_review import VerifiedPrincipal, enforce_voice_quota

def test_uncommissioned_quota_fails_closed():
    with pytest.raises(HTTPException) as error:
        asyncio.run(enforce_voice_quota(VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")))
    assert error.value.status_code == 429

def test_principal_requires_both_identifiers():
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="synthetic-user")

def test_principal_rejects_empty_identity():
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="", tenant_id="synthetic-shop")
