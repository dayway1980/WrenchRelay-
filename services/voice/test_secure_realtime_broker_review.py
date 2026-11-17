"""Synthetic contract checks: voice has no customer-facing quota gate."""
import asyncio
import pytest
from pydantic import ValidationError
from services.voice.secure_realtime_broker_review import VerifiedPrincipal, enforce_voice_quota

def test_authenticated_principal_not_blocked_by_quota():
    principal = VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    assert asyncio.run(enforce_voice_quota(principal)) is None

def test_principal_requires_both_identifiers():
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="synthetic-user")

def test_principal_rejects_empty_identity():
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="", tenant_id="synthetic-shop")
