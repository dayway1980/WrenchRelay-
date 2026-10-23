import ast
import json
from pathlib import Path


def test_health_routes_and_database_gate_are_present():
    source = Path("server.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert '@app.get("/api/health/live")' in source
    assert '@app.get("/api/health/ready")' in source
    assert "status_code=503" in source


def test_deployment_uses_readiness_probe():
    source = Path("railway.json").read_text(encoding="utf-8")
    assert '"healthcheckPath":"/api/health/ready"' in source


def test_frontend_build_uses_patched_node_runtime():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))

    assert "FROM node:22.23.4-bookworm AS frontend-build" in dockerfile
    assert package["engines"]["node"] == ">=22.23.4 <23"


def test_vercel_api_has_liveness_and_readiness_routes():
    source = Path("api-service/main.py").read_text(encoding="utf-8")
    ast.parse(source)

    assert '@app.get("/api/health/live")' in source
    assert '@app.get("/api/health/ready")' in source
    assert 'status_code=503' in source
