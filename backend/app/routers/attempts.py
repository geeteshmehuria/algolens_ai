# app/routers/attempts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_session
from app.models import ProblemAttempt, DSAProblem
from app.routers.auth import get_current_user, User
from app.services.progress_service import schedule_revision

router = APIRouter(prefix="/problems", tags=["Attempts"])

# --- Pydantic Schemas ---
class AttemptCreate(BaseModel):
    submitted_code: str
    status: str  # 'Correct', 'Incorrect', 'Reviewing'
    used_hint: bool = False
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None

# --- Endpoints ---
@router.get("/{problem_id}/attempts", response_model=List[ProblemAttempt])
def get_attempts(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all attempts by the user for a given problem"""
    statement = select(ProblemAttempt).where(
        ProblemAttempt.user_id == current_user.id,
        ProblemAttempt.problem_id == problem_id
    ).order_by(ProblemAttempt.created_on.desc())
    
    return session.exec(statement).all()


@router.post("/{problem_id}/attempts", response_model=ProblemAttempt, status_code=status.HTTP_201_CREATED)
def create_attempt(
    problem_id: int,
    attempt_data: AttemptCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Save a new problem attempt"""
    # Verify problem exists
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
        
    new_attempt = ProblemAttempt(
        user_id=current_user.id,
        problem_id=problem_id,
        submitted_code=attempt_data.submitted_code,
        status=attempt_data.status,
        used_hint=attempt_data.used_hint,
        time_complexity=attempt_data.time_complexity,
        space_complexity=attempt_data.space_complexity
    )
    
    session.add(new_attempt)

    # Solving a problem queues it for spaced revision automatically.
    if attempt_data.status == "Correct":
        schedule_revision(session, current_user.id, problem_id, reason="Solved")

    session.commit()
    session.refresh(new_attempt)
    return new_attempt
