"""Synthetic HTTP safety checks. No OpenAI request or live customer data."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from services.voice.secure_realtime_broker_review import (
    router, VerifiedPrincipal, require_verified_principal,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_unauthenticated_denied():
    assert client.post("/api/realtime/session").status_code == 403

def test_empty_identity_rejected():
    with pytest.raises(ValidationError):
        VerifiedPrincipal(user_id="", tenant_id="synthetic-shop")

def test_uncommissioned_quota_denied():
    app.dependency_overrides[require_verified_principal] = (
        lambda: VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    )
    try:
        assert client.post("/api/realtime/session").status_code == 429
    finally:
        app.dependency_overrides.clear()
