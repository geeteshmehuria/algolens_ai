# tests/test_ai_caching.py
"""Phase 3: AI content is generated once and reused — reopening a problem must
not re-call the LLM. Covers the shared explanation/animation cache and the
per-user hint cache. No per-user content table is introduced."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import get_session
from app.routers.auth import get_current_user
from app.services import ai_service, step_generators


@pytest.fixture
def client(session, user, make_problem, monkeypatch):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    # Rate limiting is irrelevant here and would conflate with cache behavior.
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    with TestClient(app) as c:
        yield c, make_problem
    app.dependency_overrides.clear()


def test_explanation_generated_once_then_served_from_cache(client, monkeypatch):
    c, make_problem = client
    problem = make_problem()

    calls = {"n": 0}

    def fake_explanation(*args, **kwargs):
        calls["n"] += 1
        return {"simple_explanation": "idea", "pseudocode": ["step 1"]}

    monkeypatch.setattr(ai_service, "generate_explanation", fake_explanation)

    first = c.post(f"/api/ai/generate-explanation/{problem.id}")
    assert first.status_code == 200
    assert first.json()["cached"] is False

    second = c.post(f"/api/ai/generate-explanation/{problem.id}")
    assert second.status_code == 200
    assert second.json()["cached"] is True

    # The LLM was hit exactly once across both opens.
    assert calls["n"] == 1


def test_animation_generated_once_then_served_from_cache(client, monkeypatch):
    c, make_problem = client
    problem = make_problem()

    calls = {"n": 0}

    def fake_steps(*args, **kwargs):
        calls["n"] += 1
        return {"animation_type": "stack", "input": {"array": []}, "steps": []}

    # Force a single deterministic generation path; cache should short-circuit #2.
    monkeypatch.setattr(step_generators, "generate_for_problem", fake_steps)

    assert c.post(f"/api/ai/generate-animation/{problem.id}").json()["cached"] is False
    assert c.post(f"/api/ai/generate-animation/{problem.id}").json()["cached"] is True
    assert calls["n"] == 1


def test_hint_cached_per_level(client, monkeypatch):
    c, make_problem = client
    problem = make_problem()

    calls = {"n": 0}

    def fake_hint(problem_, level, *args, **kwargs):
        calls["n"] += 1
        return f"hint for level {level}"

    monkeypatch.setattr(ai_service, "generate_hint", fake_hint)

    # Same level twice -> generated once, second served from DB.
    r1 = c.post("/api/ai/hint", json={"problem_id": problem.id, "hint_level": 1})
    r2 = c.post("/api/ai/hint", json={"problem_id": problem.id, "hint_level": 1})
    assert r1.json()["hint_text"] == r2.json()["hint_text"]
    assert calls["n"] == 1

    # A different level is a separate cache entry -> one more generation.
    c.post("/api/ai/hint", json={"problem_id": problem.id, "hint_level": 2})
    assert calls["n"] == 2
