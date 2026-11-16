"""HTTP fail-closed checks; no external calls or live data."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.voice.secure_realtime_broker_review import router, VerifiedPrincipal, require_verified_principal

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_uncommissioned_quota_denied():
    app.dependency_overrides[require_verified_principal] = (
        lambda: VerifiedPrincipal(user_id="synthetic-user", tenant_id="synthetic-shop")
    )
    try:
        assert client.post("/api/realtime/synthetic-shop/session").status_code == 429
    finally:
        app.dependency_overrides.clear()
