# tests/test_email_service.py
import hashlib
import logging
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.main import app
from app.models import PasswordResetToken, User
from app.services import email_service
from app.utils import hash_password


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
        email="mailtest@test.dev",
        password_hash=hash_password("SomePass123"),
        full_name="Mail Tester",
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


# --- forgot-password endpoint and the email service contract ---


def test_forgot_password_calls_email_service_with_valid_link(
    client, session, registered_user, monkeypatch
):
    sent = {}

    def fake_send(to_email, reset_link):
        sent["to"] = to_email
        sent["link"] = reset_link

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", fake_send)

    resp = client.post("/api/auth/forgot-password", json={"email": "mailtest@test.dev"})
    assert resp.status_code == 200

    assert sent["to"] == "mailtest@test.dev"
    assert sent["link"].startswith(f"{settings.FRONTEND_URL}/reset-password?token=")

    raw_token = sent["link"].split("token=", 1)[1]
    # URL-safe and high-entropy (token_urlsafe(32) → 43 chars)
    assert len(raw_token) >= 40
    assert all(c.isalnum() or c in "-_" for c in raw_token)

    # The DB stores only the SHA-256 of the raw token from the link
    stored = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == registered_user.id
        )
    ).one()
    assert stored.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert stored.token_hash != raw_token


def test_forgot_password_email_failure_is_logged_but_generic(
    client, registered_user, monkeypatch, caplog
):
    def boom(to_email, reset_link):
        raise RuntimeError("SMTP connection refused")

    monkeypatch.setattr("app.routers.auth.send_password_reset_email", boom)

    with caplog.at_level(logging.ERROR, logger="app.routers.auth"):
        resp = client.post(
            "/api/auth/forgot-password", json={"email": "mailtest@test.dev"}
        )

    # Caller still gets the same generic 200 — no enumeration, no 500
    assert resp.status_code == 200
    assert "reset link has been sent" in resp.json()["message"]
    # ...but the real failure reaches the server log
    assert any("SMTP connection refused" in r.message for r in caplog.records)


# --- SMTP layer (mocked — unit tests never send real email) ---


class FakeSMTP:
    """Stands in for smtplib.SMTP/SMTP_SSL as a context manager."""

    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.tls_started = False
        self.login_args = None
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.tls_started = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture
def smtp_settings(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.dev")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@test.dev")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")
    FakeSMTP.instances.clear()
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTP)


def test_send_email_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    with pytest.raises(RuntimeError, match="SMTP is not configured"):
        email_service.send_email("a@b.dev", "subject", "body")


def test_send_email_uses_starttls_and_auth(smtp_settings):
    email_service.send_email("rcpt@test.dev", "Hello", "plain body")

    smtp = FakeSMTP.instances[-1]
    assert (smtp.host, smtp.port) == ("smtp.test.dev", 587)
    assert smtp.tls_started is True
    assert smtp.login_args == ("sender@test.dev", "app-password")
    msg = smtp.sent[0]
    assert msg["To"] == "rcpt@test.dev"
    assert msg["Subject"] == "Hello"
    assert "sender@test.dev" in msg["From"]


def test_reset_email_contains_link_in_text_and_html(smtp_settings):
    link = "http://localhost:5173/reset-password?token=abc123"
    email_service.send_password_reset_email("rcpt@example.com", link)

    msg = FakeSMTP.instances[-1].sent[0]
    bodies = [part.get_content() for part in msg.walk() if not part.is_multipart()]
    assert len(bodies) == 2  # text + html alternative
    assert all(link in body for body in bodies)


def test_reset_email_falls_back_to_dev_outbox_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    outbox = tmp_path / "outbox.json"
    monkeypatch.setattr(email_service, "DEV_OUTBOX_PATH", outbox)

    email_service.send_password_reset_email("rcpt@test.dev", "http://x/reset?token=t")
    assert outbox.exists()
    assert "rcpt@test.dev" in outbox.read_text()


def test_dev_test_domain_goes_to_outbox_even_with_smtp(
    smtp_settings, monkeypatch, tmp_path
):
    """E2E test users (@test.dev) must never hit the real SMTP provider."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    outbox = tmp_path / "outbox.json"
    monkeypatch.setattr(email_service, "DEV_OUTBOX_PATH", outbox)

    email_service.send_password_reset_email("pw-e2e@test.dev", "http://x/reset?token=t")
    assert outbox.exists()
    assert FakeSMTP.instances == []  # no SMTP connection attempted


def test_real_recipient_uses_smtp_in_development(smtp_settings, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    email_service.send_password_reset_email(
        "person@gmail.com", "http://x/reset?token=t"
    )
    assert len(FakeSMTP.instances) == 1
    assert FakeSMTP.instances[0].sent[0]["To"] == "person@gmail.com"


def test_reset_email_refuses_silent_drop_in_production(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="SMTP is not configured|not configured"):
        email_service.send_password_reset_email("a@b.dev", "http://x/reset?token=t")
