# tests/test_latest_attempt.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.database import get_session
from app.models import AICodeReview, ProblemAttempt
from app.routers.auth import get_current_user


@pytest.fixture
def client(session: Session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_latest_attempt_empty_when_no_submission(client, make_problem):
    problem = make_problem()
    data = client.get(f"/api/problems/{problem.id}/latest-attempt").json()
    assert data["code"] is None
    assert data["ai_review"] is None


def test_latest_attempt_restores_code_and_review(
    client, session: Session, user, make_problem
):
    problem = make_problem()
    attempt = ProblemAttempt(
        user_id=user.id,
        problem_id=problem.id,
        submitted_code="def solve(): return 42",
        status="Correct",
        ai_score=88.0,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    session.add(
        AICodeReview(
            attempt_id=attempt.id,
            is_correct=True,
            logic_feedback="Looks good",
            bugs=[],
            missed_edge_cases=["empty input"],
            better_approach="use a hash map",
            dsa_pattern="Hashing",
            time_complexity="O(n)",
            space_complexity="O(n)",
            score=88.0,
        )
    )
    session.commit()

    data = client.get(f"/api/problems/{problem.id}/latest-attempt").json()
    assert data["code"] == "def solve(): return 42"
    assert data["status"] == "Correct"
    assert data["ai_review"]["is_correct"] is True
    assert data["ai_review"]["score"] == 88.0
    assert data["ai_review"]["missed_edge_cases"] == ["empty input"]


def test_latest_attempt_returns_most_recent(
    client, session: Session, user, make_problem
):
    problem = make_problem()
    for code in ["v1", "v2", "v3"]:
        session.add(
            ProblemAttempt(
                user_id=user.id,
                problem_id=problem.id,
                submitted_code=code,
                status="Incorrect",
            )
        )
        session.commit()

    data = client.get(f"/api/problems/{problem.id}/latest-attempt").json()
    assert data["code"] == "v3"


def test_latest_attempt_404_for_missing_problem(client):
    assert client.get("/api/problems/999999/latest-attempt").status_code == 404
