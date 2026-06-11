# app/services/progress_service.py
"""Spaced repetition scheduling and user progress helpers."""
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, select, func

from app.models import RevisionQueue, ProblemAttempt, DSAProblem, DSATopic

# Expanding review intervals (days): 1st review after 3 days, then 7, 16, 35.
REVISION_INTERVALS = [3, 7, 16, 35]


def schedule_revision(session: Session, user_id: int, problem_id: int, reason: str = "Spaced repetition") -> Optional[RevisionQueue]:
    """Queue the next review for a problem the user just solved/reviewed.

    The interval grows with how many reviews of this problem were already
    completed. No-op if a pending entry already exists.
    """
    pending = session.exec(
        select(RevisionQueue).where(
            RevisionQueue.user_id == user_id,
            RevisionQueue.problem_id == problem_id,
            RevisionQueue.status == "pending",
        )
    ).first()
    if pending:
        return None

    completed_count = session.exec(
        select(func.count(RevisionQueue.id)).where(
            RevisionQueue.user_id == user_id,
            RevisionQueue.problem_id == problem_id,
            RevisionQueue.status == "completed",
        )
    ).one() or 0

    interval = REVISION_INTERVALS[min(completed_count, len(REVISION_INTERVALS) - 1)]
    entry = RevisionQueue(
        user_id=user_id,
        problem_id=problem_id,
        due_date=date.today() + timedelta(days=interval),
        reason=f"{reason} (review #{completed_count + 1}, +{interval}d)",
        status="pending",
    )
    session.add(entry)
    return entry


def calculate_streak(session: Session, user_id: int) -> int:
    """Consecutive days with at least one attempt, ending today or yesterday."""
    rows = session.exec(
        select(func.date(ProblemAttempt.created_on))
        .where(ProblemAttempt.user_id == user_id)
        .distinct()
    ).all()
    if not rows:
        return 0

    # func.date may return date objects or ISO strings depending on driver.
    days = set()
    for row in rows:
        days.add(date.fromisoformat(row) if isinstance(row, str) else row)

    # Attempts are stored with UTC timestamps (created_on=utcnow), so the
    # anchor must be the UTC date too — date.today() is local and breaks
    # streaks near midnight / across timezones.
    today = datetime.utcnow().date()
    anchor = today if today in days else today - timedelta(days=1)
    if anchor not in days:
        return 0

    streak = 0
    current = anchor
    while current in days:
        streak += 1
        current -= timedelta(days=1)
    return streak


def compute_topic_proficiency(session: Session, user_id: int) -> List[dict]:
    """Per-topic proficiency from real attempts.

    score = 60% solve rate (unique problems solved / attempted)
          + 40% average AI review score (when available).
    Returns all attempted topics sorted weakest first.
    """
    attempts = session.exec(
        select(ProblemAttempt, DSAProblem.topic_id)
        .join(DSAProblem, ProblemAttempt.problem_id == DSAProblem.id)
        .where(ProblemAttempt.user_id == user_id)
    ).all()
    if not attempts:
        return []

    by_topic: dict = {}
    for attempt, topic_id in attempts:
        bucket = by_topic.setdefault(topic_id, {"attempted": set(), "solved": set(), "scores": []})
        bucket["attempted"].add(attempt.problem_id)
        if attempt.status == "Correct":
            bucket["solved"].add(attempt.problem_id)
        if attempt.ai_score is not None:
            bucket["scores"].append(attempt.ai_score)

    results = []
    for topic_id, bucket in by_topic.items():
        topic = session.get(DSATopic, topic_id)
        solve_rate = 100.0 * len(bucket["solved"]) / len(bucket["attempted"])
        if bucket["scores"]:
            avg_ai = sum(bucket["scores"]) / len(bucket["scores"])
            score = round(0.6 * solve_rate + 0.4 * avg_ai)
        else:
            score = round(solve_rate)
        results.append({
            "topic_id": topic_id,
            "topic_name": topic.name if topic else "Unknown",
            "score": score,
            "attempted": len(bucket["attempted"]),
            "solved": len(bucket["solved"]),
        })

    results.sort(key=lambda t: t["score"])
    return results


def recommend_problems(session: Session, user_id: int, limit: int = 3) -> List[dict]:
    """Unsolved active problems, weakest topics first, then easier difficulties."""
    solved_ids = set(session.exec(
        select(ProblemAttempt.problem_id).where(
            ProblemAttempt.user_id == user_id,
            ProblemAttempt.status == "Correct",
        ).distinct()
    ).all())

    weak_order = {t["topic_id"]: i for i, t in enumerate(compute_topic_proficiency(session, user_id))}
    difficulty_order = {"Easy": 0, "Medium": 1, "Hard": 2}

    problems = session.exec(select(DSAProblem).where(DSAProblem.is_active == True)).all()  # noqa: E712
    unsolved = [p for p in problems if p.id not in solved_ids]
    # Weak topics first; topics never attempted go after weak ones but before strong ones is
    # debatable — we place them in the middle so new learners still get variety.
    unsolved.sort(key=lambda p: (weak_order.get(p.topic_id, len(weak_order)), difficulty_order.get(p.difficulty, 3)))

    recommendations = []
    for p in unsolved[:limit]:
        topic = session.get(DSATopic, p.topic_id)
        recommendations.append({
            "id": p.id,
            "title": p.title,
            "difficulty": p.difficulty,
            "topic": topic.name if topic else "General",
        })
    return recommendations
