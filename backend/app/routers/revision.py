# app/routers/revision.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.database import get_session
from app.models import RevisionQueue
from app.routers.auth import get_current_user, User
from app.services.progress_service import schedule_revision

router = APIRouter(prefix="/revision", tags=["Revision Queue"])


@router.get("", response_model=List[RevisionQueue])
def get_revision_queue(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all pending and completed revision tasks for the user"""
    statement = (
        select(RevisionQueue)
        .where(RevisionQueue.user_id == current_user.id)
        .order_by(RevisionQueue.due_date.asc())
    )

    return session.exec(statement).all()


@router.post("/{revision_id}/complete", response_model=RevisionQueue)
def complete_revision(
    revision_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark a revision task as completed"""
    revision = session.get(RevisionQueue, revision_id)
    if not revision or revision.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Revision item not found"
        )

    revision.status = "completed"
    session.add(revision)
    session.commit()

    # Spaced repetition: completing a review schedules the next one at a
    # longer interval (3 -> 7 -> 16 -> 35 days).
    schedule_revision(
        session, current_user.id, revision.problem_id, reason="Spaced repetition"
    )
    session.commit()

    session.refresh(revision)
    return revision
