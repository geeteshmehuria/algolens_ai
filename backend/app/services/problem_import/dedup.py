"""Deduplication helpers for the problem-import pipeline.

A re-run of any import must never create a duplicate row. We treat three signals
as "already present":

  1. same (source_name, leetcode_slug)  — the idempotency key (also a DB unique
     index, but we check in code so the SQLite test DB and pre-commit dedup work);
  2. same leetcode_slug from ANY source — the same LeetCode problem indexed twice;
  3. same normalized title within the resolved topic — near-duplicate titles.
"""

import re

from sqlmodel import Session, select

from app.models import DSAProblem


def slugify_title(value: str) -> str:
    """Lowercase, collapse any run of non-alphanumerics into a single hyphen.

    Mirrors ``app.seed.curriculum.slugify`` so titles normalize consistently
    across the codebase."""
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def find_duplicate(
    session: Session,
    *,
    source_name: str | None,
    leetcode_slug: str | None,
    title_slug: str,
    topic_id: int | None,
) -> DSAProblem | None:
    """Return an existing problem that this candidate duplicates, else None."""
    if source_name and leetcode_slug:
        existing = session.exec(
            select(DSAProblem).where(
                DSAProblem.source_name == source_name,
                DSAProblem.leetcode_slug == leetcode_slug,
            )
        ).first()
        if existing:
            return existing

    if leetcode_slug:
        existing = session.exec(
            select(DSAProblem).where(DSAProblem.leetcode_slug == leetcode_slug)
        ).first()
        if existing:
            return existing

    if title_slug and topic_id is not None:
        existing = session.exec(
            select(DSAProblem).where(
                DSAProblem.title_slug == title_slug,
                DSAProblem.topic_id == topic_id,
            )
        ).first()
        if existing:
            return existing

    return None
