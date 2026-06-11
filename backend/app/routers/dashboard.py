# app/routers/dashboard.py
from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from pydantic import BaseModel
from typing import List, Dict, Any

from app.database import get_session
from app.models import ProblemAttempt, RevisionQueue
from app.routers.auth import get_current_user, User
from app.services.progress_service import (
    calculate_streak,
    compute_topic_proficiency,
    recommend_problems,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

class DashboardSummary(BaseModel):
    solved_count: int
    attempted_count: int
    streak: int
    revision_due_count: int
    weak_topics: List[Dict[str, Any]]
    recommended_problems: List[Dict[str, Any]]

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Summary statistics for the user dashboard — all computed from real
    attempts, never placeholder data."""
    attempted_count = session.exec(
        select(func.count(func.distinct(ProblemAttempt.problem_id))).where(
            ProblemAttempt.user_id == current_user.id
        )
    ).one() or 0

    solved_count = session.exec(
        select(func.count(func.distinct(ProblemAttempt.problem_id))).where(
            ProblemAttempt.user_id == current_user.id,
            ProblemAttempt.status == "Correct"
        )
    ).one() or 0

    # Only revisions actually due (today or overdue), not everything pending.
    revision_due_count = session.exec(
        select(func.count(RevisionQueue.id)).where(
            RevisionQueue.user_id == current_user.id,
            RevisionQueue.status == "pending",
            RevisionQueue.due_date <= date.today(),
        )
    ).one() or 0

    streak = calculate_streak(session, current_user.id)

    # Weakest 3 topics the user has actually attempted.
    weak_topics = [
        {"topic_name": t["topic_name"], "score": t["score"]}
        for t in compute_topic_proficiency(session, current_user.id)[:3]
    ]

    recommended_problems = recommend_problems(session, current_user.id, limit=3)

    return DashboardSummary(
        solved_count=solved_count,
        attempted_count=attempted_count,
        streak=streak,
        revision_due_count=revision_due_count,
        weak_topics=weak_topics,
        recommended_problems=recommended_problems,
    )
