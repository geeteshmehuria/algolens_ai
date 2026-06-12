# app/services/email_service.py
"""Outbound email via SMTP.

When SMTP is configured (see app.config.Settings), real emails are sent in
every environment. When it is not configured, development falls back to a
local outbox file + console print; any other environment fails loudly.
"""

import json
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Dev-only stand-in for an email inbox: the most recent "email" is written
# here so humans and E2E tests can pick up the reset link. Gitignored.
DEV_OUTBOX_PATH = Path(__file__).resolve().parents[2] / "scratch" / "dev_outbox.json"


def smtp_configured() -> bool:
    return bool(
        settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD
    )


def send_email(
    to_email: str, subject: str, text_body: str, html_body: Optional[str] = None
) -> None:
    """Send one email over SMTP. Raises on any failure — callers decide
    whether to swallow (e.g. forgot-password must stay generic)."""
    if not smtp_configured():
        raise RuntimeError(
            "SMTP is not configured: set SMTP_HOST, SMTP_USERNAME and "
            "SMTP_PASSWORD in backend/.env (see .env.example)."
        )

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            s.send_message(msg)


def _dev_outbox_recipient(to_email: str) -> bool:
    """In development, test-domain recipients bypass real SMTP so E2E runs
    never send fake addresses through the real provider (bounces hurt
    sender reputation)."""
    if settings.ENVIRONMENT != "development":
        return False
    domains = [
        d.strip().lower()
        for d in settings.EMAIL_DEV_OUTBOX_DOMAINS.split(",")
        if d.strip()
    ]
    return any(to_email.lower().endswith("@" + d) for d in domains)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if smtp_configured() and not _dev_outbox_recipient(to_email):
        minutes = settings.RESET_TOKEN_EXPIRE_MINUTES
        text_body = (
            "We received a request to reset your AlgoLens AI password.\n\n"
            f"Open this link to choose a new password (valid for {minutes} minutes):\n"
            f"{reset_link}\n\n"
            "If you didn't request this, you can safely ignore this email — "
            "your password will not change."
        )
        html_body = f"""\
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #0f172a;">
    <div style="max-width: 480px; margin: 0 auto; padding: 24px;">
      <h2 style="color: #2563eb;">AlgoLens AI</h2>
      <p>We received a request to reset your password.</p>
      <p>
        <a href="{reset_link}"
           style="display: inline-block; background: #2563eb; color: #ffffff;
                  padding: 10px 20px; border-radius: 8px; text-decoration: none;">
          Reset Password
        </a>
      </p>
      <p style="color: #64748b; font-size: 13px;">
        This link is valid for {minutes} minutes. If the button doesn't work,
        copy this URL into your browser:<br>
        <a href="{reset_link}">{reset_link}</a>
      </p>
      <p style="color: #64748b; font-size: 13px;">
        If you didn't request this, you can safely ignore this email —
        your password will not change.
      </p>
    </div>
  </body>
</html>
"""
        send_email(to_email, "Reset your AlgoLens AI password", text_body, html_body)
        # Deliberately no reset_link/token here — only the recipient
        logger.info("Password reset email sent to %s", to_email)
        return

    if settings.ENVIRONMENT == "development":
        # Dev-only fallback when SMTP isn't configured: surface the link on
        # stdout and in the dev outbox file. The raw token must never be
        # printed/logged outside development.
        print(
            f"[DEV ONLY] Password reset link for {to_email}: {reset_link}",
            flush=True,  # stdout is piped under uvicorn; unflushed output stalls
        )
        env_file = Path(__file__).resolve().parents[2] / ".env"
        DEV_OUTBOX_PATH.parent.mkdir(exist_ok=True)
        DEV_OUTBOX_PATH.write_text(
            json.dumps(
                {
                    "to": to_email,
                    "reset_link": reset_link,
                    "sent_at": datetime.utcnow().isoformat(),
                    # why the fallback ran — booleans only, never values
                    "diag": {
                        "smtp_host_set": bool(settings.SMTP_HOST),
                        "smtp_user_set": bool(settings.SMTP_USERNAME),
                        "smtp_pass_set": bool(settings.SMTP_PASSWORD),
                        "env_file_exists": env_file.exists(),
                    },
                }
            ),
            encoding="utf-8",
        )
        return

    raise RuntimeError(
        "Cannot send password reset email: SMTP is not configured and "
        f"ENVIRONMENT={settings.ENVIRONMENT!r} does not allow the dev fallback."
    )
