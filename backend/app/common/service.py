# app/common/service.py
"""Builders for the common bootstrap + master-data payloads.

Kept thin and read-only; all heavy/user logic is reused from existing services
and models so this module never becomes a second source of truth.
"""

from datetime import datetime
from typing import Iterable, Set

from sqlmodel import Session, select

from app.config import settings
from app.models import DSAPattern, DSATopic, User
from app.routers.auth import get_user_role_names
from app.services.progress_service import learning_summary

from app.common.schemas import (
    ContentsResponse,
    ContentsUser,
    MasterDataResponse,
    PatternOption,
    TopicOption,
)

# Languages the solver currently supports (the editor/runner is Python-only today).
SUPPORTED_LANGUAGES = ["python"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]

# Master-data keys this endpoint knows how to serve. Unknown keys are ignored
# rather than erroring, so the client can request optimistically.
MASTER_DATA_KEYS = {"topics", "patterns", "difficulties", "languages"}


def _permissions_for(roles: Iterable[str]) -> list[str]:
    """Coarse capability list derived from roles (no secrets, UI-hint only —
    the backend still enforces real authorization on every route)."""
    perms: list[str] = []
    if "admin" in roles:
        perms.append("content:manage")
    return perms


def build_contents(session: Session, user: User) -> ContentsResponse:
    roles = get_user_role_names(session, user.id)
    return ContentsResponse(
        user=ContentsUser(
            id=user.id,
            name=user.full_name,
            email=user.email,
            roles=roles,
            permissions=_permissions_for(roles),
        ),
        preferences={
            "leetcode_username": user.leetcode_username,
        },
        feature_flags={
            # Real, non-sensitive capability flags the UI can branch on.
            "ai_enabled": bool(settings.GOOGLE_GEMINI_API_KEY),
            "email_enabled": bool(settings.SMTP_HOST),
            "rate_limit_enabled": bool(settings.RATE_LIMIT_ENABLED),
        },
        app_config={
            # Safe, public config. Keeps the editor/validators in sync with the
            # backend without a separate call. No secrets, no URLs.
            "app_name": "AlgoLens AI",
            "max_code_length": 20000,
            "supported_languages": SUPPORTED_LANGUAGES,
        },
        learning_summary=learning_summary(session, user.id),
        version=datetime.utcnow().isoformat() + "Z",
    )


def parse_keys(keys: str | None) -> Set[str]:
    """Parse the comma-separated ?keys= query into a known-key set."""
    if not keys:
        return set()
    requested = {k.strip().lower() for k in keys.split(",") if k.strip()}
    return requested & MASTER_DATA_KEYS


def build_master_data(session: Session, keys: Set[str]) -> MasterDataResponse:
    resp = MasterDataResponse()

    if "topics" in keys:
        topics = session.exec(select(DSATopic).order_by(DSATopic.name)).all()
        resp.topics = [TopicOption(id=t.id, name=t.name) for t in topics]

    if "patterns" in keys:
        patterns = session.exec(select(DSAPattern).order_by(DSAPattern.name)).all()
        resp.patterns = [
            PatternOption(id=p.id, name=p.name, topic_id=p.topic_id) for p in patterns
        ]

    if "difficulties" in keys:
        resp.difficulties = list(DIFFICULTIES)

    if "languages" in keys:
        resp.languages = list(SUPPORTED_LANGUAGES)

    return resp
