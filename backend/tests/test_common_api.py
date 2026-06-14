# tests/test_common_api.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.database import get_session
from app.models import ProblemAttempt, Role, UserRole
from app.routers.auth import get_current_user


@pytest.fixture
def client(session: Session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- /common/contents ---


def test_contents_returns_user_flags_and_summary(
    client, session: Session, user, make_problem
):
    problem = make_problem()
    session.add(
        ProblemAttempt(
            user_id=user.id, problem_id=problem.id, submitted_code="x", status="Correct"
        )
    )
    session.commit()

    res = client.get("/api/common/contents")
    assert res.status_code == 200
    data = res.json()

    assert data["user"]["id"] == user.id
    assert data["user"]["email"] == user.email
    assert data["user"]["roles"] == []  # no role rows -> empty
    # learning_summary is real, computed from the attempt above
    assert data["learning_summary"]["solved_count"] == 1
    assert data["learning_summary"]["attempted_count"] == 1
    # feature flags + version present
    assert set(["ai_enabled", "email_enabled", "rate_limit_enabled"]).issubset(
        data["feature_flags"].keys()
    )
    assert data["version"]


def test_contents_never_leaks_token_or_password(client, session: Session):
    data = client.get("/api/common/contents").json()
    blob = str(data).lower()
    assert "password" not in blob
    assert "token" not in blob


def test_contents_reflects_admin_role(client, session: Session, user):
    role = Role(name="admin")
    session.add(role)
    session.commit()
    session.refresh(role)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()

    data = client.get("/api/common/contents").json()
    assert "admin" in data["user"]["roles"]
    assert "content:manage" in data["user"]["permissions"]


def test_contents_requires_auth():
    # No dependency override here -> real auth runs and rejects the anonymous call.
    with TestClient(app) as c:
        assert c.get("/api/common/contents").status_code in (401, 403)


# --- /common/master-data ---


def test_master_data_returns_only_requested_keys(
    client, session: Session, make_problem
):
    # make_problem seeds a topic + pattern
    make_problem()

    res = client.get("/api/common/master-data?keys=topics,difficulties")
    assert res.status_code == 200
    data = res.json()

    assert data["topics"] is not None and len(data["topics"]) >= 1
    assert data["difficulties"] == ["Easy", "Medium", "Hard"]
    # Unrequested keys stay null so the payload is minimal
    assert data["patterns"] is None
    assert data["languages"] is None


def test_master_data_patterns_and_languages(client, session: Session, make_problem):
    make_problem()
    data = client.get("/api/common/master-data?keys=patterns,languages").json()
    assert data["patterns"] is not None and len(data["patterns"]) >= 1
    assert "topic_id" in data["patterns"][0]
    assert data["languages"] == ["python"]
    assert data["topics"] is None


def test_master_data_unknown_and_empty_keys(client, session: Session):
    # Unknown keys are ignored; no keys -> everything null.
    assert client.get("/api/common/master-data?keys=foo,bar").json() == {
        "topics": None,
        "patterns": None,
        "difficulties": None,
        "languages": None,
    }
    assert client.get("/api/common/master-data").json()["topics"] is None
