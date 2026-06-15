"""Tests for the DSA curriculum seeder (app/seed/curriculum.py)."""

from sqlmodel import select

from app.models import DSAPattern, DSAProblem, DSATopic
from app.seed.curriculum import seed_curriculum, slugify
from app.seed.curriculum_data import CURRICULUM


def _all_curriculum_names():
    names = []
    for cat in CURRICULUM:
        for name, _difficulty, _desc in cat["topics"]:
            names.append(name)
    return names


def test_curriculum_names_and_slugs_are_globally_unique():
    names = _all_curriculum_names()
    assert len(names) == len(set(names)), "Duplicate topic name in curriculum data"
    slugs = [slugify(n) for n in names]
    assert len(slugs) == len(set(slugs)), "Duplicate derived slug in curriculum data"


def test_seed_creates_full_curriculum(session):
    expected = len(_all_curriculum_names())
    stats = seed_curriculum(session)

    assert stats["created"] == expected
    assert stats["updated"] == 0
    assert stats["total"] == expected

    topics = session.exec(select(DSATopic)).all()
    assert len(topics) == expected
    # Every topic carries full metadata.
    for t in topics:
        assert t.slug
        assert t.category
        assert t.difficulty in ("beginner", "intermediate", "advanced")
        assert t.learning_order and t.learning_order > 0
        assert t.estimated_time_minutes and t.estimated_time_minutes > 0
        assert isinstance(t.tags, list) and t.tags
        assert isinstance(t.prerequisites, list)
        assert t.is_active is True


def test_seed_is_idempotent(session):
    first = seed_curriculum(session)
    count_after_first = len(session.exec(select(DSATopic)).all())
    patterns_after_first = len(session.exec(select(DSAPattern)).all())

    second = seed_curriculum(session)
    count_after_second = len(session.exec(select(DSATopic)).all())
    patterns_after_second = len(session.exec(select(DSAPattern)).all())

    # No new rows on the second run.
    assert count_after_first == count_after_second
    assert patterns_after_first == patterns_after_second
    assert second["created"] == 0
    assert second["updated"] == first["total"]
    assert second["patterns_created"] == 0


def test_every_topic_has_a_default_pattern(session):
    seed_curriculum(session)
    topics = session.exec(select(DSATopic)).all()
    topic_ids_with_pattern = set(session.exec(select(DSAPattern.topic_id)).all())
    for t in topics:
        assert t.id in topic_ids_with_pattern


def test_legacy_topic_is_reconciled_in_place(session):
    """A pre-existing 'Stack' topic (with a linked problem) must be merged into
    'Stack Basics' keeping its id, so problem links survive."""
    legacy = DSATopic(name="Stack", description="old desc")
    session.add(legacy)
    session.commit()
    session.refresh(legacy)
    legacy_id = legacy.id

    pattern = DSAPattern(topic_id=legacy_id, name="Stack", description="")
    session.add(pattern)
    session.commit()
    session.refresh(pattern)

    problem = DSAProblem(
        title="Valid Parentheses",
        difficulty="Easy",
        topic_id=legacy_id,
        pattern_id=pattern.id,
        description="desc",
    )
    session.add(problem)
    session.commit()

    seed_curriculum(session)

    # The legacy row is now the canonical "Stack Basics" topic, same id.
    reconciled = session.get(DSATopic, legacy_id)
    assert reconciled.name == "Stack Basics"
    assert reconciled.slug == "stack-basics"
    assert reconciled.category == "Stack"

    # No duplicate "Stack Basics" was created.
    stack_basics = session.exec(
        select(DSATopic).where(DSATopic.slug == "stack-basics")
    ).all()
    assert len(stack_basics) == 1

    # Problem link is intact.
    refreshed_problem = session.get(DSAProblem, problem.id)
    assert refreshed_problem.topic_id == legacy_id


def test_existing_description_not_clobbered(session):
    long_desc = "A very detailed hand-written description that should be preserved."
    existing = DSATopic(name="Two Pointers", description=long_desc)
    session.add(existing)
    session.commit()

    seed_curriculum(session)

    topic = session.exec(
        select(DSATopic).where(DSATopic.slug == "two-pointers")
    ).first()
    assert topic.description == long_desc
