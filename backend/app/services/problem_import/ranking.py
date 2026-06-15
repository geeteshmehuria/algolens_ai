"""Coverage-aware ranking so imports fill gaps instead of arriving randomly.

Priority order (highest first):
  1. Easy problems for categories below their coverage target (beginner value);
  2. Common interview problems (sources that carry an interview-frequency score);
  3. Medium, then Hard.

``run_import`` ranks all candidates and keeps the top ``daily_limit``.
"""

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import DSAProblem, DSATopic
from app.services.problem_import.topic_map import TAG_TO_CATEGORY, slugify_title

# Per-category target problem counts (from the project brief). Two Pointers /
# Sliding Window fold into "Arrays" because that is where those topics live.
TOPIC_COVERAGE_TARGETS: dict[str, int] = {
    "Arrays": 20,
    "Strings": 15,
    "Hashing": 15,
    "Stack": 10,
    "Queue and Deque": 8,
    "Linked List": 12,
    "Searching": 12,
    "Trees": 20,
    "Graphs": 20,
    "Dynamic Programming": 25,
    "Greedy Algorithms": 12,
    "Heap / Priority Queue": 10,
    "Recursion and Backtracking": 12,
    "Bit Manipulation": 10,
    "Math for DSA": 10,
}

_DIFFICULTY_WEIGHT = {"easy": 3.0, "medium": 2.0, "hard": 1.0}


def category_for_tag(tag: str) -> str | None:
    """Best-effort category name for a coarse import tag."""
    return TAG_TO_CATEGORY.get(slugify_title(tag))


def coverage_counts(session: Session) -> dict[str, int]:
    """Current non-archived problem count per curriculum category."""
    rows = session.exec(
        select(DSATopic.category, func.count(DSAProblem.id))
        .join(DSAProblem, DSAProblem.topic_id == DSATopic.id)
        .where(
            DSAProblem.is_active == True,  # noqa: E712
            DSAProblem.import_status != "archived",
        )
        .group_by(DSATopic.category)
    ).all()
    return {cat: count for cat, count in rows if cat}


def coverage_snapshot(session: Session) -> list[dict]:
    """Per-category {category, current, target, gap}, sorted by largest gap."""
    counts = coverage_counts(session)
    snapshot = []
    for category, target in TOPIC_COVERAGE_TARGETS.items():
        current = counts.get(category, 0)
        snapshot.append(
            {
                "category": category,
                "current": current,
                "target": target,
                "gap": max(0, target - current),
            }
        )
    snapshot.sort(key=lambda r: r["gap"], reverse=True)
    return snapshot


def _priority(candidate, counts: dict[str, int]) -> float:
    """Higher = imported sooner. Drives the learning_priority_score too."""
    difficulty = (candidate.difficulty or "").lower()
    score = _DIFFICULTY_WEIGHT.get(difficulty, 1.5) * 10.0

    category = category_for_tag(candidate.topic_tag)
    if category:
        target = TOPIC_COVERAGE_TARGETS.get(category, 0)
        gap = max(0, target - counts.get(category, 0))
        score += float(gap)  # under-covered categories rise

    if candidate.interview_frequency_score:
        score += float(candidate.interview_frequency_score)
    return score


def rank_candidates(session: Session, candidates: list) -> list:
    """Annotate each candidate with learning_priority_score and sort, best first."""
    counts = coverage_counts(session)
    for c in candidates:
        c.learning_priority_score = round(_priority(c, counts), 3)
    return sorted(candidates, key=lambda c: c.learning_priority_score, reverse=True)
