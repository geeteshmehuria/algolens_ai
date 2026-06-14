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

# The built-in development JWT secret. It is intentionally well-known, so it
# must never sign tokens in production — _validate_production_config() blocks
# startup if it (or an empty value) survives into a non-development env.
DEFAULT_JWT_SECRET = "supersecretjwtkeyforalgolensai1234567890!@#"

# Environment names treated as "local / not production" — these relax the
# config guard and keep the localhost CORS origins.
_NON_PROD_ENVS = {"development", "dev", "local", "test", "testing"}


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/algolens_db"

    # Security
    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Abuse protection. In-process sliding-window rate limiting (see
    # app/services/rate_limit.py) guards auth and AI endpoints. Disable only
    # for special test scenarios; production should keep it on.
    RATE_LIMIT_ENABLED: bool = True

    # Comma-separated additional CORS origins (e.g. the deployed frontend).
    # FRONTEND_URL is always allowed; localhost origins are added only in
    # non-production environments.
    CORS_ORIGINS: str = ""

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() not in _NON_PROD_ENVS

    def allowed_cors_origins(self) -> list[str]:
        """Origins allowed by CORS. The deployed frontend (FRONTEND_URL) and
        any CORS_ORIGINS entries are always included; localhost dev origins are
        added only outside production."""
        origins: list[str] = []
        if self.FRONTEND_URL:
            origins.append(self.FRONTEND_URL.rstrip("/"))
        origins.extend(
            o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()
        )
        if not self.is_production:
            origins.extend(
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:5174",
                    "http://127.0.0.1:5174",
                ]
            )
        # De-duplicate while preserving order.
        seen: set[str] = set()
        return [o for o in origins if not (o in seen or seen.add(o))]


def _validate_production_config(s: "Settings") -> None:
    """Fail fast on insecure production configuration.

    In local/dev environments we only warn; in production a weak JWT secret or
    a missing frontend origin aborts startup so the app never serves traffic in
    a forgeable-token state.
    """
    if not s.is_production:
        if s.JWT_SECRET == DEFAULT_JWT_SECRET:
            logger.warning(
                "Using the built-in default JWT_SECRET — acceptable for local "
                "development only. Set a strong unique JWT_SECRET before deploying."
            )
        return

    errors: list[str] = []
    if not s.JWT_SECRET or s.JWT_SECRET == DEFAULT_JWT_SECRET:
        errors.append(
            "JWT_SECRET must be set to a strong, unique value (not the built-in "
            "default) when ENVIRONMENT is not 'development'."
        )
    elif len(s.JWT_SECRET) < 32:
        errors.append("JWT_SECRET should be at least 32 characters long.")
    if not s.allowed_cors_origins():
        errors.append(
            "Set FRONTEND_URL (and/or CORS_ORIGINS) to your production frontend "
            "origin so CORS is not left empty."
        )
    if errors:
        raise RuntimeError(
            "Refusing to start with insecure production configuration:\n  - "
            + "\n  - ".join(errors)
        )


settings = Settings()
_validate_production_config(settings)
