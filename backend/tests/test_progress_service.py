from datetime import date, datetime, timedelta

from sqlmodel import select

from app.models import ProblemAttempt, RevisionQueue
from app.services.progress_service import (
    REVISION_INTERVALS,
    schedule_revision,
    calculate_streak,
    compute_topic_proficiency,
    recommend_problems,
)


def _attempt(session, user, problem, status="Correct", days_ago=0, ai_score=None):
    a = ProblemAttempt(
        user_id=user.id,
        problem_id=problem.id,
        submitted_code="code",
        status=status,
        ai_score=ai_score,
        created_on=datetime.utcnow() - timedelta(days=days_ago),
    )
    session.add(a)
    session.commit()
    return a


# --- schedule_revision ---


def test_first_revision_due_in_three_days(session, user, make_problem):
    problem = make_problem()
    schedule_revision(session, user.id, problem.id)
    session.commit()

    entry = session.exec(select(RevisionQueue)).one()
    assert entry.due_date == date.today() + timedelta(days=REVISION_INTERVALS[0])
    assert entry.status == "pending"
    assert "review #1" in entry.reason


def test_no_duplicate_pending_revision(session, user, make_problem):
    problem = make_problem()
    schedule_revision(session, user.id, problem.id)
    session.commit()
    assert schedule_revision(session, user.id, problem.id) is None
    session.commit()
    assert len(session.exec(select(RevisionQueue)).all()) == 1


def test_intervals_grow_with_completed_reviews(session, user, make_problem):
    problem = make_problem()
    # Two completed reviews already on record -> next interval is the third (16d).
    for _ in range(2):
        session.add(
            RevisionQueue(
                user_id=user.id,
                problem_id=problem.id,
                due_date=date.today(),
                status="completed",
            )
        )
    session.commit()

    entry = schedule_revision(session, user.id, problem.id)
    session.commit()
    assert entry.due_date == date.today() + timedelta(days=REVISION_INTERVALS[2])


def test_interval_caps_at_last_value(session, user, make_problem):
    problem = make_problem()
    for _ in range(10):
        session.add(
            RevisionQueue(
                user_id=user.id,
                problem_id=problem.id,
                due_date=date.today(),
                status="completed",
            )
        )
    session.commit()

    entry = schedule_revision(session, user.id, problem.id)
    session.commit()
    assert entry.due_date == date.today() + timedelta(days=REVISION_INTERVALS[-1])


# --- calculate_streak ---


def test_streak_zero_without_attempts(session, user):
    assert calculate_streak(session, user.id) == 0


def test_streak_counts_consecutive_days(session, user, make_problem):
    problem = make_problem()
    for days_ago in (0, 1, 2):
        _attempt(session, user, problem, days_ago=days_ago)
    assert calculate_streak(session, user.id) == 3


def test_streak_broken_by_gap(session, user, make_problem):
    problem = make_problem()
    for days_ago in (0, 1, 3, 4):  # gap at 2 days ago
        _attempt(session, user, problem, days_ago=days_ago)
    assert calculate_streak(session, user.id) == 2


def test_streak_survives_missing_today(session, user, make_problem):
    # Practiced yesterday and the day before but not yet today -> streak still 2.
    problem = make_problem()
    for days_ago in (1, 2):
        _attempt(session, user, problem, days_ago=days_ago)
    assert calculate_streak(session, user.id) == 2


def test_streak_zero_when_last_activity_too_old(session, user, make_problem):
    problem = make_problem()
    _attempt(session, user, problem, days_ago=3)
    assert calculate_streak(session, user.id) == 0


# --- compute_topic_proficiency ---


def test_proficiency_solve_rate_only(session, user, make_problem):
    p1 = make_problem(title="P1")
    p2 = make_problem(title="P2")
    _attempt(session, user, p1, status="Correct")
    _attempt(session, user, p2, status="Incorrect")

    [topic] = compute_topic_proficiency(session, user.id)
    assert topic["score"] == 50  # 1 of 2 solved, no AI scores
    assert topic["attempted"] == 2
    assert topic["solved"] == 1


def test_proficiency_blends_ai_scores(session, user, make_problem):
    p1 = make_problem(title="P1")
    _attempt(session, user, p1, status="Correct", ai_score=80.0)

    [topic] = compute_topic_proficiency(session, user.id)
    # 0.6 * 100 (solve rate) + 0.4 * 80 (AI score) = 92
    assert topic["score"] == 92


def test_proficiency_sorted_weakest_first(session, user, make_problem):
    strong = make_problem(title="S", topic="Stack", pattern="Stack")
    weak = make_problem(title="W", topic="Binary Search", pattern="Binary Search")
    _attempt(session, user, strong, status="Correct")
    _attempt(session, user, weak, status="Incorrect")

    topics = compute_topic_proficiency(session, user.id)
    assert topics[0]["topic_name"] == "Binary Search"
    assert topics[0]["score"] < topics[1]["score"]


# --- recommend_problems ---


def test_recommendations_exclude_solved(session, user, make_problem):
    solved = make_problem(title="Solved One")
    make_problem(title="Unsolved One")
    _attempt(session, user, solved, status="Correct")

    recs = recommend_problems(session, user.id, limit=5)
    titles = [r["title"] for r in recs]
    assert "Unsolved One" in titles
    assert "Solved One" not in titles


def test_recommendations_prioritize_weak_topics(session, user, make_problem):
    weak_p = make_problem(
        title="Weak Topic Problem", topic="Binary Search", pattern="Binary Search"
    )
    strong_p = make_problem(
        title="Strong Topic Problem", topic="Stack", pattern="Stack"
    )
    make_problem(title="Another Weak", topic="Binary Search", pattern="Binary Search")
    _attempt(session, user, weak_p, status="Incorrect")  # Binary Search is weak (0%)
    _attempt(session, user, strong_p, status="Correct")  # Stack is strong (100%)

    recs = recommend_problems(session, user.id, limit=2)
    # Weak-topic problems come first.
    assert recs[0]["topic"] == "Binary Search"
