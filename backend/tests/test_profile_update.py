# tests/test_profile_update.py
"""PUT /api/auth/me — profile updates limited to safe fields."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import get_session
from app.main import app
from app.routers.auth import get_current_user


@pytest.fixture
def client(session: Session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_update_profile_fields(client, session, user):
    resp = client.put(
        "/api/auth/me",
        json={"full_name": "New Name", "leetcode_username": "lc_ninja"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "New Name"
    assert body["leetcode_username"] == "lc_ninja"

    session.refresh(user)
    assert user.full_name == "New Name"
    assert user.leetcode_username == "lc_ninja"


def test_partial_update_leaves_other_fields(client, session, user):
    client.put("/api/auth/me", json={"full_name": "Only Name"})
    session.refresh(user)
    assert user.full_name == "Only Name"
    # leetcode_username untouched (was None)
    assert user.leetcode_username is None


def test_email_cannot_be_changed_via_profile(client, session, user):
    original_email = user.email
    resp = client.put(
        "/api/auth/me",
        json={"email": "hacker@evil.dev", "full_name": "X"},
    )
    assert resp.status_code == 200  # unknown fields ignored by schema
    session.refresh(user)
    assert user.email == original_email


def test_whitespace_only_values_become_null(client, session, user):
    client.put("/api/auth/me", json={"leetcode_username": "   "})
    session.refresh(user)
    assert user.leetcode_username is None


def test_update_requires_auth():
    app.dependency_overrides.clear()
    with TestClient(app) as anon:
        resp = anon.put("/api/auth/me", json={"full_name": "X"})
    assert resp.status_code in (401, 403)
