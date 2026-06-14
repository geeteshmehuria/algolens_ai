# app/routers/attempts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from app.database import get_session
from app.models import ProblemAttempt, DSAProblem
from app.routers.auth import get_current_user, User
from app.services.progress_service import schedule_revision

router = APIRouter(prefix="/problems", tags=["Attempts"])

MAX_CODE_CHARS = 20_000


# --- Pydantic Schemas ---
class AttemptCreate(BaseModel):
    submitted_code: str = Field(max_length=MAX_CODE_CHARS)
    status: Literal["Correct", "Incorrect", "Reviewing"]
    used_hint: bool = False
    time_complexity: Optional[str] = Field(default=None, max_length=50)
    space_complexity: Optional[str] = Field(default=None, max_length=50)


# --- Endpoints ---
@router.get("/{problem_id}/attempts", response_model=List[ProblemAttempt])
def get_attempts(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all attempts by the user for a given problem"""
    statement = (
        select(ProblemAttempt)
        .where(
            ProblemAttempt.user_id == current_user.id,
            ProblemAttempt.problem_id == problem_id,
        )
        .order_by(ProblemAttempt.created_on.desc())
    )

    return session.exec(statement).all()


@router.post(
    "/{problem_id}/attempts",
    response_model=ProblemAttempt,
    status_code=status.HTTP_201_CREATED,
)
def create_attempt(
    problem_id: int,
    attempt_data: AttemptCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Save a new problem attempt"""
    # Verify problem exists
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )

    new_attempt = ProblemAttempt(
        user_id=current_user.id,
        problem_id=problem_id,
        submitted_code=attempt_data.submitted_code,
        status=attempt_data.status,
        used_hint=attempt_data.used_hint,
        time_complexity=attempt_data.time_complexity,
        space_complexity=attempt_data.space_complexity,
    )

    session.add(new_attempt)

    # Solving a problem queues it for spaced revision automatically.
    if attempt_data.status == "Correct":
        schedule_revision(session, current_user.id, problem_id, reason="Solved")

    session.commit()
    session.refresh(new_attempt)
    return new_attempt
