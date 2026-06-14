# tests/test_security_hardening.py
"""Coverage for the pre-deployment hardening: production config guard, rate
limiting, request-size limits, and bounded catalog pagination."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import DEFAULT_JWT_SECRET, Settings, _validate_production_config
from app.database import get_session
from app.main import app
from app.routers.auth import get_current_user
from app.services import rate_limit


@pytest.fixture
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(session: Session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- Production config guard ---------------------------------------------


def test_production_rejects_default_jwt_secret():
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET=DEFAULT_JWT_SECRET,
        FRONTEND_URL="https://app.example.com",
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _validate_production_config(s)


def test_production_rejects_empty_cors():
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        FRONTEND_URL="",
        CORS_ORIGINS="",
    )
    with pytest.raises(RuntimeError, match="CORS"):
        _validate_production_config(s)


def test_production_accepts_strong_config():
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="a-strong-unique-secret-value-of-decent-length-123",
        FRONTEND_URL="https://app.example.com",
    )
    _validate_production_config(s)  # must not raise


def test_development_allows_default_secret():
    s = Settings(ENVIRONMENT="development", JWT_SECRET=DEFAULT_JWT_SECRET)
    _validate_production_config(s)  # warns only, must not raise


def test_dev_cors_includes_localhost_but_prod_does_not():
    dev = Settings(ENVIRONMENT="development", FRONTEND_URL="https://app.example.com")
    assert "http://localhost:5173" in dev.allowed_cors_origins()
    assert "https://app.example.com" in dev.allowed_cors_origins()

    prod = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        FRONTEND_URL="https://app.example.com",
    )
    assert prod.allowed_cors_origins() == ["https://app.example.com"]


def test_production_rejects_localhost_only_cors():
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        FRONTEND_URL="http://localhost:5173",
        CORS_ORIGINS="http://127.0.0.1:5173",
    )
    with pytest.raises(RuntimeError, match="localhost origins"):
        _validate_production_config(s)


def test_cors_origin_normalization():
    # If no protocol is provided, it should normalize to both https and http
    s = Settings(
        ENVIRONMENT="production",
        FRONTEND_URL="algolens-ai.vercel.app",
        CORS_ORIGINS="other-app.vercel.app/,https://explicit.com",
    )
    allowed = s.allowed_cors_origins()
    assert "https://algolens-ai.vercel.app" in allowed
    assert "http://algolens-ai.vercel.app" in allowed
    assert "https://other-app.vercel.app" in allowed
    assert "http://other-app.vercel.app" in allowed
    assert "https://explicit.com" in allowed
    assert "http://explicit.com" not in allowed


# --- Rate limiting --------------------------------------------------------


def test_login_is_rate_limited(client):
    rate_limit.reset_all()
    # login_limiter allows 10 per 60s; the 11th from the same client is 429.
    last = None
    for _ in range(11):
        last = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.dev", "password": "whatever"},
        )
    assert last.status_code == 429
    assert "Retry-After" in last.headers


def test_rate_limit_can_be_disabled(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    rate_limit.reset_all()
    codes = {
        client.post(
            "/api/auth/login",
            json={"email": "nobody@test.dev", "password": "x"},
        ).status_code
        for _ in range(15)
    }
    assert 429 not in codes


# --- Request size limits --------------------------------------------------


def test_register_rejects_overlong_name(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "n@test.dev", "password": "Pass12345", "full_name": "x" * 200},
    )
    assert resp.status_code == 422


def test_attempt_rejects_oversized_code(authed_client, make_problem):
    problem = make_problem()
    resp = authed_client.post(
        f"/api/problems/{problem.id}/attempts",
        json={"submitted_code": "x" * 20_001, "status": "Reviewing"},
    )
    assert resp.status_code == 422


def test_attempt_rejects_unknown_status(authed_client, make_problem):
    problem = make_problem()
    resp = authed_client.post(
        f"/api/problems/{problem.id}/attempts",
        json={"submitted_code": "print(1)", "status": "Hacked"},
    )
    assert resp.status_code == 422


# --- Pagination -----------------------------------------------------------


def test_problems_pagination_limits_results(client, make_problem):
    for i in range(5):
        make_problem(title=f"P{i}")
    page = client.get("/api/problems?limit=2").json()
    assert len(page) == 2


def test_problems_rejects_oversized_limit(client):
    resp = client.get("/api/problems?limit=5000")
    assert resp.status_code == 422
