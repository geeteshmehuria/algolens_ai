# app/services/request_log.py
"""Writes failures to the ``t_log`` table.

Logging must never break a request, so nothing here raises. Query it with SQL,
e.g. ``SELECT created_at, method, path, status, error FROM t_log ORDER BY id DESC LIMIT 20;``
"""

import logging
from datetime import datetime, timedelta
from typing import Callable

from sqlmodel import Session, delete

from app.database import engine
from app.models import TLog

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30
_LIMITS = {"path": 200, "origin": 200, "user_agent": 200, "error": 2000}

# Swappable so tests write to their in-memory DB instead of the real one.
session_factory: Callable[[], Session] = lambda: Session(engine)  # noqa: E731


def describe(exc: BaseException) -> str:
    """'message | CauseType: cause' — keeps the real reason behind friendly HTTP
    errors (e.g. the Gemini 429 quota text behind a generic 502)."""
    text = str(getattr(exc, "detail", None) or exc)
    cause = exc.__cause__ or exc.__context__
    return f"{text} | {type(cause).__name__}: {cause}" if cause else text


def record(method: str, path: str, **fields) -> None:
    values = {"path": path, **fields}
    values = {
        k: (v[: _LIMITS[k]] if k in _LIMITS and isinstance(v, str) else v)
        for k, v in values.items()
    }
    try:
        with session_factory() as db:
            db.add(TLog(method=method, **values))
            db.commit()
    except Exception as e:  # e.g. DB down — the error is already in the server log
        logger.warning("could not write t_log: %s", e)


def prune(days: int = RETENTION_DAYS) -> None:
    try:
        with session_factory() as db:
            cutoff = datetime.utcnow() - timedelta(days=days)
            db.exec(delete(TLog).where(TLog.created_at < cutoff))
            db.commit()
    except Exception as e:
        logger.warning("could not prune t_log: %s", e)
