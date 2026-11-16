"""Safety regression tests for the review-only voice broker.

These assert fail-closed behavior. They do not prove an authenticated voice
session works and must not be used as release approval.
"""
import asyncio
import pytest
from fastapi import HTTPException
from services.voice.secure_realtime_broker_review import (
    VerifiedPrincipal, require_verified_principal, enforce_voice_quota,
)

def test_missing_authentication_fails_closed():
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_verified_principal(None))
    assert error.value.status_code == 403

def test_uncommissioned_quota_fails_closed():
    principal = VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    with pytest.raises(HTTPException) as error:
        asyncio.run(enforce_voice_quota(principal))
    assert error.value.status_code == 429

def test_principal_requires_both_identifiers():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="synthetic-user")
