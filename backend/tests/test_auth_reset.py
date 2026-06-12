# tests/test_auth_reset.py
import hashlib
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.database import get_session
from app.models import User, PasswordResetToken
from app.utils import hash_password, verify_password

GENERIC = "If an account exists for this email, a reset link has been sent."


@pytest.fixture
def client(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(session: Session):
    u = User(
        email="reset@test.dev",
        password_hash=hash_password("OldPass123"),
        full_name="Reset Tester",
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def _issue_token(session: Session, user: User, raw="rawtokenvalue", minutes=30):
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_on=datetime.utcnow() + timedelta(minutes=minutes),
    )
    session.add(prt)
    session.commit()
    session.refresh(prt)
    return raw, prt


# --- login email normalization ---


def test_login_is_case_insensitive(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": "ReSeT@TEST.dev", "password": "OldPass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_register_stores_lowercase_email(client, session):
    resp = client.post(
        "/api/auth/register",
        json={"email": "NewUser@Test.DEV", "password": "Pass12345", "full_name": "N"},
    )
    assert resp.status_code == 201
    user = session.exec(select(User).where(User.email == "newuser@test.dev")).first()
    assert user is not None


def test_register_rejects_password_over_72_bytes(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "long@test.dev", "password": "x" * 80, "full_name": "L"},
    )
    assert resp.status_code == 422


# --- forgot-password ---


def test_forgot_password_known_email(client, session, registered_user):
    resp = client.post("/api/auth/forgot-password", json={"email": "reset@test.dev"})
    assert resp.status_code == 200
    assert resp.json()["message"] == GENERIC
    tokens = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == registered_user.id
        )
    ).all()
    assert len(tokens) == 1
    assert tokens[0].used_on is None
    assert len(tokens[0].token_hash) == 64  # sha256 hex, never the raw token


def test_forgot_password_unknown_email_same_response(client, session):
    resp = client.post("/api/auth/forgot-password", json={"email": "nobody@test.dev"})
    assert resp.status_code == 200
    assert resp.json()["message"] == GENERIC
    assert session.exec(select(PasswordResetToken)).all() == []


def test_forgot_password_invalidates_previous_tokens(client, session, registered_user):
    raw, old = _issue_token(session, registered_user)
    # Age the old token past the 60s throttle window
    old.created_on = datetime.utcnow() - timedelta(minutes=5)
    session.add(old)
    session.commit()

    client.post("/api/auth/forgot-password", json={"email": "reset@test.dev"})

    session.refresh(old)
    assert old.used_on is not None  # invalidated
    active = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == registered_user.id,
            PasswordResetToken.used_on == None,  # noqa: E711
        )
    ).all()
    assert len(active) == 1


# --- reset-password ---


def test_reset_password_happy_path(client, session, registered_user):
    raw, prt = _issue_token(session, registered_user)

    resp = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "NewPass456",
            "confirm_password": "NewPass456",
        },
    )
    assert resp.status_code == 200

    session.refresh(registered_user)
    session.refresh(prt)
    assert verify_password("NewPass456", registered_user.password_hash)
    assert not verify_password("OldPass123", registered_user.password_hash)
    assert prt.used_on is not None

    ok = client.post(
        "/api/auth/login",
        json={"email": "reset@test.dev", "password": "NewPass456"},
    )
    assert ok.status_code == 200
    bad = client.post(
        "/api/auth/login",
        json={"email": "reset@test.dev", "password": "OldPass123"},
    )
    assert bad.status_code == 401


def test_reset_password_invalid_token(client, session, registered_user):
    resp = client.post(
        "/api/auth/reset-password",
        json={
            "token": "not-a-real-token",
            "new_password": "NewPass456",
            "confirm_password": "NewPass456",
        },
    )
    assert resp.status_code == 400


def test_reset_password_expired_token(client, session, registered_user):
    raw, _ = _issue_token(session, registered_user, minutes=-1)
    resp = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "NewPass456",
            "confirm_password": "NewPass456",
        },
    )
    assert resp.status_code == 400


def test_reset_password_token_single_use(client, session, registered_user):
    raw, _ = _issue_token(session, registered_user)
    first = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "NewPass456",
            "confirm_password": "NewPass456",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "Another789",
            "confirm_password": "Another789",
        },
    )
    assert second.status_code == 400


def test_reset_password_mismatch(client, session, registered_user):
    raw, _ = _issue_token(session, registered_user)
    resp = client.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "NewPass456",
            "confirm_password": "Different456",
        },
    )
    assert resp.status_code == 400


def test_reset_password_too_short(client, session, registered_user):
    raw, _ = _issue_token(session, registered_user)
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw, "new_password": "short", "confirm_password": "short"},
    )
    assert resp.status_code == 422
