# app/config.py
import logging
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _clear_stale_tls_env() -> None:
    """Drop TLS override env vars that point at files which no longer exist.

    A leftover SSL_CERT_FILE from an uninstalled tool (e.g. Miniconda's
    cacert.pem) makes every TLS client in the process — httpx (Gemini),
    smtplib (password-reset email) — fail with FileNotFoundError. A path
    that doesn't exist provides no security; removing it process-locally
    restores the default certifi/system trust store.
    """
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and not os.path.isfile(path):
            logger.warning(
                "Ignoring %s=%s — file does not exist; using default CA bundle",
                var,
                path,
            )
            del os.environ[var]
    cert_dir = os.environ.get("SSL_CERT_DIR")
    if cert_dir and not os.path.isdir(cert_dir):
        logger.warning("Ignoring SSL_CERT_DIR=%s — directory does not exist", cert_dir)
        del os.environ["SSL_CERT_DIR"]


_clear_stale_tls_env()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/algolens_db"

    # Security
    JWT_SECRET: str = "supersecretjwtkeyforalgolensai1234567890!@#"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Password reset
    FRONTEND_URL: str = "http://localhost:5173"
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # 'development' falls back to logging reset links locally when SMTP is
    # not configured; any other value requires working SMTP settings
    ENVIRONMENT: str = "development"

    # SMTP email delivery. When all four required values are set, real
    # emails are sent (in every environment). Gmail example:
    #   SMTP_HOST=smtp.gmail.com, SMTP_PORT=587,
    #   SMTP_USERNAME=you@gmail.com, SMTP_PASSWORD=<16-char App Password>
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587  # 587 = STARTTLS, 465 = implicit SSL
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""  # defaults to SMTP_USERNAME when empty
    SMTP_FROM_NAME: str = "AlgoLens AI"

    # In development, recipients on these domains (comma-separated) are
    # written to the dev outbox instead of real SMTP, so E2E tests never
    # push fake addresses through the real mail provider.
    EMAIL_DEV_OUTBOX_DOMAINS: str = "test.dev"

    # AI Configuration (Google Gemini)
    GOOGLE_GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Pydantic Configuration
    # This instructs pydantic to load from backend/.env if it exists
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
