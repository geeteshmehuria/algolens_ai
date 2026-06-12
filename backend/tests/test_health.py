# tests/test_health.py
"""App startup, root endpoint, and route-mounting smoke checks."""

from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint_reports_online():
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "online"
    assert body["app"] == "AlgoLens AI API"


def test_openapi_schema_loads():
    with TestClient(app) as client:
        resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert len(resp.json()["paths"]) > 30


def test_expected_router_prefixes_mounted():
    paths = {route.path for route in app.routes}
    for expected in [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/me",
        "/api/topics",
        "/api/problems",
        "/api/dashboard/summary",
    ]:
        assert expected in paths, f"route missing: {expected}"


def test_user_scoped_endpoints_reject_anonymous():
    with TestClient(app) as client:
        for path in ["/api/auth/me", "/api/dashboard/summary", "/api/revision"]:
            resp = client.get(path)
            # HTTPBearer returns 403 when the header is absent
            assert resp.status_code in (401, 403), f"{path} returned {resp.status_code}"


def test_invalid_jwt_rejected():
    with TestClient(app) as client:
        resp = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer not.a.real.jwt"}
        )
    assert resp.status_code == 401
