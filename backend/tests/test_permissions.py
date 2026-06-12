# tests/test_permissions.py
"""Role-based access: every admin-only endpoint must reject a regular user."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import get_session
from app.main import app
from app.routers.auth import get_current_user


@pytest.fixture
def user_client(session: Session, user):
    """Client authenticated as a regular (non-admin) user."""

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


ADMIN_ONLY = [
    (
        "POST",
        "/api/problems",
        {
            "title": "X",
            "difficulty": "Easy",
            "topic_id": 1,
            "pattern_id": 1,
            "description": "d",
        },
    ),
    (
        "POST",
        "/api/problems/import-leetcode-url",
        {"url": "https://leetcode.com/problems/two-sum/"},
    ),
    ("GET", "/api/topics/1/notes/versions", None),
    ("PATCH", "/api/topic-notes/1", {"content": {}}),
    ("POST", "/api/topic-notes/1/publish", None),
    ("POST", "/api/topics/1/notes/regenerate", None),
]


@pytest.mark.parametrize("method,path,body", ADMIN_ONLY)
def test_admin_endpoints_reject_regular_user(user_client, method, path, body):
    resp = user_client.request(method, path, json=body)
    assert resp.status_code == 403, (
        f"{method} {path} returned {resp.status_code}, expected 403 for non-admin"
    )
    assert "Admin privileges required" in resp.json()["detail"]
