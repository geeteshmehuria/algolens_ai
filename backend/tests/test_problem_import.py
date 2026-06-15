# tests/test_problem_import.py
"""Tests for the automated problem-import pipeline."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import get_session
from app.main import app
from app.models import (
    AIGeneratedContent,
    DSAPattern,
    DSAProblem,
    DSATopic,
    ProblemImportRun,
)
from app.routers.auth import get_current_user
from app.services.problem_import import ai_content
from app.services.problem_import.runner import run_import
from app.services.problem_import.sources import ImportCandidate


# --- Helpers / fixtures ---
def _make_topic(session: Session, name: str, category: str, order: int) -> DSATopic:
    topic = DSATopic(
        name=name,
        slug=name.lower().replace(" ", "-"),
        category=category,
        learning_order=order,
        is_active=True,
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    session.add(DSAPattern(topic_id=topic.id, name=f"{name} Pattern"))
    session.commit()
    return topic


@pytest.fixture
def seeded_topics(session: Session):
    """Topics with categories so the tag resolver can map candidates."""
    _make_topic(session, "Two Pointers", "Arrays", 101)
    _make_topic(session, "Valid Parentheses Stack", "Stack", 401)
    _make_topic(session, "Hash Maps", "Hashing", 478)
    return session


def _candidate(title, tag, difficulty="Easy", slug=None, **kw):
    return ImportCandidate(
        title=title,
        difficulty=difficulty,
        topic_tag=tag,
        source_type="manual",
        source_name="test",
        leetcode_slug=slug,
        **kw,
    )


class _ListSource:
    """A trivial in-test source returning fixed candidates."""

    name = "test_list"

    def __init__(self, candidates):
        self._candidates = candidates

    def fetch(self, session, limit):
        return list(self._candidates)


class _BrokenSource:
    name = "broken"

    def fetch(self, session, limit):
        raise RuntimeError("boom")


# --- Service-level tests ---
def test_import_creates_problems_and_logs_run(session, seeded_topics):
    source = _ListSource(
        [
            _candidate("Alpha", "arrays", slug="alpha"),
            _candidate("Beta", "stack", slug="beta"),
            _candidate("Gamma", "hashing", difficulty="Medium", slug="gamma"),
        ]
    )
    run = run_import(session, trigger="manual", sources=[source], daily_limit=10)

    assert run.status == "success"
    assert run.imported_count == 3
    assert run.skipped_duplicate_count == 0
    assert run.failed_count == 0

    problems = session.exec(select(DSAProblem)).all()
    assert len(problems) == 3
    assert all(p.import_status == "review_required" for p in problems)
    assert all(p.source_name == "test" for p in problems)
    assert all(p.title_slug for p in problems)

    # The run itself is logged.
    runs = session.exec(select(ProblemImportRun)).all()
    assert len(runs) == 1 and runs[0].id == run.id


def test_reimport_does_not_duplicate(session, seeded_topics):
    source = _ListSource([_candidate("Alpha", "arrays", slug="alpha")])
    first = run_import(session, trigger="manual", sources=[source], daily_limit=10)
    second = run_import(session, trigger="manual", sources=[source], daily_limit=10)

    assert first.imported_count == 1
    assert second.imported_count == 0
    assert second.skipped_duplicate_count == 1
    assert len(session.exec(select(DSAProblem)).all()) == 1


def test_duplicate_by_title_within_topic(session, seeded_topics):
    """Same normalized title in the same topic is treated as a duplicate even
    without a shared slug."""
    src1 = _ListSource([_candidate("Two Sum", "arrays", slug="two-sum")])
    src2 = _ListSource([_candidate("two sum", "arrays")])  # no slug, same title
    run_import(session, trigger="manual", sources=[src1], daily_limit=10)
    run = run_import(session, trigger="manual", sources=[src2], daily_limit=10)
    assert run.imported_count == 0
    assert run.skipped_duplicate_count == 1


def test_unmapped_topic_is_failed_not_crash(session, seeded_topics):
    source = _ListSource([_candidate("Orphan", "no-such-topic", slug="orphan")])
    run = run_import(session, trigger="manual", sources=[source], daily_limit=10)
    assert run.imported_count == 0
    assert run.failed_count == 1
    assert run.status == "failed"
    assert "Unmapped topic" in (run.error_log or "")


def test_failing_source_handled_gracefully(session, seeded_topics):
    good = _ListSource([_candidate("Alpha", "arrays", slug="alpha")])
    run = run_import(
        session, trigger="manual", sources=[_BrokenSource(), good], daily_limit=10
    )
    assert run.imported_count == 1  # the good source still ran
    assert run.status == "partial"
    assert "broken" in (run.error_log or "")


def test_daily_limit_caps_imports(session, seeded_topics):
    source = _ListSource(
        [
            _candidate("A", "arrays", slug="a"),
            _candidate("B", "stack", slug="b"),
            _candidate("C", "hashing", slug="c"),
        ]
    )
    run = run_import(session, trigger="manual", sources=[source], daily_limit=2)
    assert run.imported_count == 2
    assert len(session.exec(select(DSAProblem)).all()) == 2


def test_easy_low_coverage_ranked_first(session, seeded_topics):
    """With a limit of 1, the Easy candidate for a high-gap topic wins."""
    source = _ListSource(
        [
            _candidate("HardOne", "arrays", difficulty="Hard", slug="hard"),
            _candidate("EasyOne", "arrays", difficulty="Easy", slug="easy"),
        ]
    )
    run = run_import(session, trigger="manual", sources=[source], daily_limit=1)
    assert run.imported_count == 1
    imported = session.exec(select(DSAProblem)).first()
    assert imported.title == "EasyOne"


def test_ai_learning_pack_persisted_on_import(session, seeded_topics):
    pack = {
        "explanation": "e",
        "approach": "a",
        "pseudocode": "p",
        "hints": ["h"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "beginner_notes": "n",
        "test_cases": [{"input": "1", "expected_output": "1"}],
    }
    source = _ListSource(
        [_candidate("WithPack", "arrays", slug="wp", ai_learning_pack=pack)]
    )
    run_import(session, trigger="manual", sources=[source], daily_limit=10)
    problem = session.exec(select(DSAProblem)).first()
    cached = session.exec(
        select(AIGeneratedContent).where(
            AIGeneratedContent.problem_id == problem.id,
            AIGeneratedContent.kind == "learning_pack",
        )
    ).first()
    assert cached is not None
    assert cached.content["time_complexity"] == "O(n)"


def test_learning_pack_generated_once_and_reused(session, seeded_topics, monkeypatch):
    source = _ListSource([_candidate("NoPack", "arrays", slug="np")])
    run_import(session, trigger="manual", sources=[source], daily_limit=10)
    problem = session.exec(select(DSAProblem)).first()

    calls = {"n": 0}
    fake_pack = {
        "explanation": "e",
        "approach": "a",
        "pseudocode": "p",
        "hints": ["h"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "beginner_notes": "n",
        "test_cases": [],
    }

    def fake_generate(problem, topic_name="", pattern_name=""):
        calls["n"] += 1
        return fake_pack

    monkeypatch.setattr(ai_content, "ai_available", lambda: True)
    monkeypatch.setattr(ai_content, "generate_learning_pack", fake_generate)

    first = ai_content.get_or_create_learning_pack(session, problem)
    second = ai_content.get_or_create_learning_pack(session, problem)
    assert first["cached"] is False
    assert second["cached"] is True
    assert calls["n"] == 1  # generated once, then served from cache


# --- Endpoint tests ---
@pytest.fixture
def user_client(session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def public_client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/admin/problem-import/run"),
        ("GET", "/api/admin/problem-import/runs"),
        ("GET", "/api/admin/problem-import/status"),
        ("GET", "/api/admin/problem-import/problems"),
        ("POST", "/api/admin/problem-import/problems/1/publish"),
        ("POST", "/api/admin/problem-import/upload"),
    ],
)
def test_admin_endpoints_reject_regular_user(user_client, method, path):
    resp = user_client.request(method, path, json={})
    assert resp.status_code == 403
    assert "Admin privileges required" in resp.json()["detail"]


def test_public_catalog_hides_review_required(public_client, session, seeded_topics):
    source = _ListSource([_candidate("Hidden", "arrays", slug="hidden")])
    run_import(session, trigger="manual", sources=[source], daily_limit=10)
    # Imported problem is review_required -> excluded from the public catalog.
    resp = public_client.get("/api/problems")
    assert resp.status_code == 200
    assert resp.json() == []

    # Publishing it makes it visible.
    problem = session.exec(select(DSAProblem)).first()
    problem.import_status = "published"
    session.add(problem)
    session.commit()
    resp = public_client.get("/api/problems")
    assert len(resp.json()) == 1
