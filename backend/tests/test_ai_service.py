# tests/test_ai_service.py
"""Gemini integration: config hygiene, retry behavior, JSON correction,
and frontend-safe router errors. No real Gemini calls — client is mocked."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from app.config import _clear_stale_tls_env, settings
from app.database import get_session
from app.main import app
from app.routers.auth import get_current_user
from app.services import ai_service
from app.services.ai_service import AIGenerationError, AIUnavailableError


# --- stale TLS env cleanup (the [Errno 2] root cause) ---


def test_stale_ssl_cert_file_is_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "deleted" / "cacert.pem"))
    _clear_stale_tls_env()
    assert "SSL_CERT_FILE" not in os.environ


def test_valid_ssl_cert_file_is_kept(monkeypatch, tmp_path):
    cert = tmp_path / "cacert.pem"
    cert.write_text("dummy")
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    _clear_stale_tls_env()
    assert os.environ.get("SSL_CERT_FILE") == str(cert)


def test_stale_requests_ca_bundle_is_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path / "gone.pem"))
    _clear_stale_tls_env()
    assert "REQUESTS_CA_BUNDLE" not in os.environ


# --- _generate_json behavior with a fake client ---


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, outcomes):
        # each outcome: an Exception to raise or a string to return
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(ai_service.time, "sleep", lambda s: None)  # no real waits


def _install_client(monkeypatch, outcomes) -> FakeClient:
    client = FakeClient(outcomes)
    monkeypatch.setattr(ai_service, "_get_client", lambda: client)
    return client


def test_generate_json_success(with_api_key, monkeypatch):
    _install_client(monkeypatch, ['{"ok": true}'])
    assert ai_service._generate_json("prompt") == {"ok": True}


def test_generate_json_strips_markdown_fences(with_api_key, monkeypatch):
    _install_client(monkeypatch, ['```json\n{"ok": true}\n```'])
    assert ai_service._generate_json("prompt") == {"ok": True}


def test_no_api_key_raises_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_GEMINI_API_KEY", "")
    with pytest.raises(AIUnavailableError):
        ai_service._generate_json("prompt")


def test_transient_error_is_retried(with_api_key, monkeypatch):
    err = Exception("quota")
    err.code = 429
    client = _install_client(monkeypatch, [err, '{"ok": true}'])
    assert ai_service._generate_json("prompt") == {"ok": True}
    assert client.models.calls == 2


def test_non_transient_error_fails_fast(with_api_key, monkeypatch):
    err = Exception("invalid api key")
    err.code = 401
    client = _install_client(monkeypatch, [err, '{"ok": true}'])
    with pytest.raises(AIGenerationError, match="Gemini request failed"):
        ai_service._generate_json("prompt")
    assert client.models.calls == 1  # no retry on auth errors


def test_transient_error_gives_up_after_max_attempts(with_api_key, monkeypatch):
    errs = []
    for _ in range(ai_service._MAX_ATTEMPTS):
        e = Exception("server error")
        e.code = 503
        errs.append(e)
    client = _install_client(monkeypatch, errs)
    with pytest.raises(AIGenerationError):
        ai_service._generate_json("prompt")
    assert client.models.calls == ai_service._MAX_ATTEMPTS


def test_empty_response_raises(with_api_key, monkeypatch):
    _install_client(monkeypatch, [""])
    with pytest.raises(AIGenerationError, match="empty response"):
        ai_service._generate_json("prompt")


def test_invalid_json_retried_once_with_correction(with_api_key, monkeypatch):
    client = _install_client(monkeypatch, ["not json at all", '{"fixed": true}'])
    assert ai_service._generate_json("prompt") == {"fixed": True}
    assert client.models.calls == 2


def test_invalid_json_twice_raises(with_api_key, monkeypatch):
    client = _install_client(monkeypatch, ["garbage one", "garbage two"])
    with pytest.raises(AIGenerationError, match="invalid JSON after retry"):
        ai_service._generate_json("prompt")
    assert client.models.calls == 2


# --- router error mapping: frontend never sees provider internals ---


@pytest.fixture
def client(session, user, make_problem):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c, make_problem
    app.dependency_overrides.clear()


def test_ai_endpoint_503_when_key_missing(client, monkeypatch):
    c, make_problem = client
    problem = make_problem(title="Hint Target")
    monkeypatch.setattr(settings, "GOOGLE_GEMINI_API_KEY", "")
    resp = c.post("/api/ai/hint", json={"problem_id": problem.id, "hint_level": 1})
    assert resp.status_code == 503
    assert "GOOGLE_GEMINI_API_KEY" in resp.json()["detail"]  # config guidance OK


def test_ai_endpoint_502_hides_provider_error(client, monkeypatch):
    c, make_problem = client
    problem = make_problem(title="Hint Target 2")

    def boom(*args, **kwargs):
        raise AIGenerationError(
            "Gemini request failed: [Errno 2] No such file or directory"
        )

    monkeypatch.setattr(ai_service, "generate_hint", boom)
    resp = c.post("/api/ai/hint", json={"problem_id": problem.id, "hint_level": 1})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "Errno" not in detail
    assert "No such file" not in detail
    assert "try again" in detail.lower()


def test_non_ai_endpoints_work_without_gemini(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(settings, "GOOGLE_GEMINI_API_KEY", "")
    assert c.get("/api/auth/me").status_code == 200
    assert c.get("/api/dashboard/summary").status_code == 200
    assert c.get("/api/problems").status_code == 200


def test_prompt_asks_for_strict_json():
    """Every prompt built on _TUTOR_RULES demands JSON-only output."""
    assert "ONLY with valid JSON" in ai_service._TUTOR_RULES


def test_generate_json_roundtrip_through_public_function(
    with_api_key, monkeypatch, make_problem_payload=None
):
    payload = {
        "simple_explanation": "x",
        "brute_force": "x",
        "optimized_approach": "x",
        "pseudocode": ["a"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "common_mistakes": ["m"],
        "pattern": "Hashing",
    }
    _install_client(monkeypatch, [json.dumps(payload)])

    from app.models import DSAProblem

    problem = DSAProblem(
        title="T",
        difficulty="Easy",
        topic_id=1,
        pattern_id=1,
        description="d",
        examples=[],
    )
    out = ai_service.generate_explanation(problem)
    assert out["pattern"] == "Hashing"
