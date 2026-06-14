# tests/test_run_tests.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.database import get_session
from app.routers.auth import get_current_user


@pytest.fixture
def client(session: Session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_run_tests_returns_examples_without_executing(client, make_problem):
    problem = make_problem(
        examples=[
            {"input": "nums=[2,7], target=9", "output": "[0,1]"},
            {"input": "nums=[3,3], target=6", "output": "[0,1]"},
        ]
    )
    res = client.post(
        f"/api/problems/{problem.id}/run-tests",
        json={"code": "def solve(): pass", "language": "python"},
    )
    assert res.status_code == 200
    data = res.json()

    # Never fakes execution / pass-fail.
    assert data["execution_supported"] is False
    assert data["passed"] == 0 and data["failed"] == 0
    assert data["total"] == 2
    assert len(data["cases"]) == 2
    assert all(c["status"] == "manual" and c["actual"] is None for c in data["cases"])
    assert data["cases"][0]["expected"] == "[0,1]"


def test_run_tests_no_examples(client, make_problem):
    problem = make_problem(examples=[])
    data = client.post(
        f"/api/problems/{problem.id}/run-tests", json={"code": "x"}
    ).json()
    assert data["total"] == 0
    assert data["cases"] == []


def test_run_tests_404_for_missing_problem(client):
    res = client.post("/api/problems/999999/run-tests", json={"code": "x"})
    assert res.status_code == 404


def test_run_tests_rejects_oversized_code(client, make_problem):
    problem = make_problem()
    res = client.post(
        f"/api/problems/{problem.id}/run-tests",
        json={"code": "x" * 20_001},
    )
    assert res.status_code == 422
