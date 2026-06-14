# app/routers/dashboard.py
from fastapi import APIRouter, Depends
from sqlmodel import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from app.database import get_session
from app.routers.auth import get_current_user, User
from app.services.progress_service import (
    compute_topic_proficiency,
    daily_activity,
    learning_summary,
    recommend_problems,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ActivityDay(BaseModel):
    date: str
    count: int


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
    current_user: User = Depends(get_current_user),
):
    """Summary statistics for the user dashboard — all computed from real
    attempts, never placeholder data."""
    # Core counters come from the shared helper (also used by /common/contents).
    summary = learning_summary(session, current_user.id)

    # Weakest 3 topics the user has actually attempted. topic_id lets the
    # dashboard deep-link each row to the filtered problems list.
    weak_topics = [
        {"topic_id": t["topic_id"], "topic_name": t["topic_name"], "score": t["score"]}
        for t in compute_topic_proficiency(session, current_user.id)[:3]
    ]

    recommended_problems = recommend_problems(session, current_user.id, limit=3)

    return DashboardSummary(
        solved_count=summary["solved_count"],
        attempted_count=summary["attempted_count"],
        streak=summary["streak"],
        revision_due_count=summary["revision_due_count"],
        weak_topics=weak_topics,
        recommended_problems=recommended_problems,
    )


@router.get("/activity", response_model=List[ActivityDay])
def get_activity(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Per-day attempt counts (last 12 weeks) for the contribution heatmap."""
    return daily_activity(session, current_user.id, days=84)
