from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.models import TLog
from app.services import request_log

# Test-only routes that fail the way real AI endpoints do.
_router = APIRouter()


@_router.get("/__test/ai-fail")
def _ai_fail():
    try:
        raise RuntimeError("429 RESOURCE_EXHAUSTED per day limit exceeded")
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI response could not be generated")


@_router.get("/__test/boom")
def _boom():
    raise ValueError("unexpected crash")


app.include_router(_router)


def _rows(engine):
    with Session(engine) as s:
        return s.exec(select(TLog).order_by(TLog.id)).all()


def test_failed_request_logs_underlying_cause(_isolate_failure_log):
    with TestClient(app) as c:
        r = c.get("/__test/ai-fail?secret=x", headers={"user-agent": "pytest"})
    assert r.status_code == 502
    assert r.json()["detail"] == "AI response could not be generated"  # client stays generic
    (row,) = _rows(_isolate_failure_log)
    assert (row.method, row.path, row.status) == ("GET", "/__test/ai-fail", 502)
    assert "RuntimeError: 429 RESOURCE_EXHAUSTED" in row.error  # real cause kept
    assert row.user_agent == "pytest"
    assert row.created_at is not None


def test_unhandled_exception_logged_as_500(_isolate_failure_log):
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/__test/boom")
    assert r.status_code == 500
    (row,) = _rows(_isolate_failure_log)
    assert row.status == 500 and "ValueError: unexpected crash" in row.error


def test_successful_request_not_logged(_isolate_failure_log):
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
    assert _rows(_isolate_failure_log) == []


def test_record_never_raises_when_db_fails(monkeypatch):
    def broken():
        raise RuntimeError("db down")

    monkeypatch.setattr(request_log, "session_factory", broken)
    request_log.record("GET", "/x", status=500)  # must not raise
