"""Synthetic HTTP checks: no provider call or live user data."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.voice.secure_realtime_broker_review import router, VerifiedPrincipal, require_verified_principal

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_uncommissioned_feature_flag_denied(monkeypatch):
    monkeypatch.delenv("WR_VOICE_COMMISSIONED", raising=False)
    app.dependency_overrides[require_verified_principal] = (
        lambda: VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    )
    try:
        assert client.post("/api/realtime/synthetic-shop/session").status_code == 503
    finally:
        app.dependency_overrides.clear()

def test_cookie_request_without_origin_denied(monkeypatch):
    monkeypatch.setenv("WR_VOICE_COMMISSIONED", "true")
    app.dependency_overrides[require_verified_principal] = (
        lambda: VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    )
    try:
        response = client.post("/api/realtime/synthetic-shop/session",cookies={"wr_access":"synthetic"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
