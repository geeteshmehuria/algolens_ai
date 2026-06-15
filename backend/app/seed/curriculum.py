"""Idempotent seeder for the DSA curriculum (``curriculum_data.CURRICULUM``).

Upserts every topic into ``dsa_topics`` keyed on a slug derived from its name,
so running the seed repeatedly never creates duplicates. Existing/legacy topics
are reconciled by name (and the ``LEGACY_ALIASES`` map) so their problem links
are preserved. Each topic also gets a default ``dsa_patterns`` row when it has
none, keeping admin problem-creation (which needs a ``pattern_id``) working.

No user data is ever deleted and topic rows are never truncated.
"""

import re
from datetime import datetime

from sqlmodel import Session, select

from app.models import DSAPattern, DSATopic
from app.seed.curriculum_data import (
    CURRICULUM,
    DIFFICULTY_MINUTES,
    LEGACY_ALIASES,
)


def slugify(value: str) -> str:
    """Lowercase, replace any run of non-alphanumerics with a single hyphen."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug


def _iter_entries():
    """Flatten CURRICULUM into ordered entry dicts with computed metadata."""
    for cat_index, category in enumerate(CURRICULUM):
        cat_name = category["category"]
        cat_slug = slugify(cat_name)
        prereqs = category.get("prerequisites", [])
        for topic_index, (name, difficulty, description) in enumerate(
            category["topics"]
        ):
            tags = [cat_slug]
            if cat_slug == "interview-patterns":
                tags.append("interview-pattern")
            yield {
                "name": name,
                "slug": slugify(name),
                "category": cat_name,
                "difficulty": difficulty,
                # 101, 102, ... 201, 202 — stable, sparse, sortable order.
                "learning_order": (cat_index + 1) * 100 + (topic_index + 1),
                "estimated_time_minutes": DIFFICULTY_MINUTES.get(difficulty, 30),
                "prerequisites": list(prereqs),
                "tags": tags,
                "description": description,
            }


def seed_curriculum(session: Session) -> dict:
    """Upsert the full curriculum. Safe to run any number of times.

    Returns counts: {"created", "updated", "patterns_created", "total"}.
    """
    existing = session.exec(select(DSATopic)).all()
    by_slug = {t.slug: t for t in existing if t.slug}
    by_name = {t.name: t for t in existing}

    created = 0
    updated = 0
    now = datetime.utcnow()

    for entry in _iter_entries():
        topic = by_slug.get(entry["slug"]) or by_name.get(entry["name"])
        # Reconcile a legacy row (e.g. "Stack" -> "Stack Basics") by its old name.
        if topic is None:
            legacy_name = LEGACY_ALIASES.get(entry["name"])
            if legacy_name:
                topic = by_name.get(legacy_name)

        if topic is None:
            topic = DSATopic(name=entry["name"])
            created += 1
        else:
            updated += 1

        topic.name = entry["name"]
        topic.slug = entry["slug"]
        topic.category = entry["category"]
        topic.difficulty = entry["difficulty"]
        topic.learning_order = entry["learning_order"]
        topic.estimated_time_minutes = entry["estimated_time_minutes"]
        topic.prerequisites = entry["prerequisites"]
        topic.tags = entry["tags"]
        topic.is_active = True
        # Only fill the description when missing, so hand-edited or AI-enriched
        # descriptions are never clobbered on a reseed.
        if not topic.description:
            topic.description = entry["description"]
        topic.updated_on = now

        session.add(topic)
        # Keep the in-run lookups fresh so duplicates within one pass can't slip in.
        by_slug[topic.slug] = topic
        by_name[topic.name] = topic

    session.commit()

    patterns_created = _ensure_default_patterns(session)

    return {
        "created": created,
        "updated": updated,
        "patterns_created": patterns_created,
        "total": created + updated,
    }


def _ensure_default_patterns(session: Session) -> int:
    """Give every topic at least one pattern so problems can be mapped to it
    (dsa_problems.pattern_id is NOT NULL). Existing patterns are left alone."""
    topics = session.exec(select(DSATopic)).all()
    # A single-column select yields scalar values, not row tuples.
    topics_with_pattern = set(session.exec(select(DSAPattern.topic_id)).all())

    created = 0
    for topic in topics:
        if topic.id in topics_with_pattern:
            continue
        session.add(
            DSAPattern(
                topic_id=topic.id,
                name=topic.name[:150],
                description=topic.description,
            )
        )
        created += 1

    if created:
        session.commit()
    return created
