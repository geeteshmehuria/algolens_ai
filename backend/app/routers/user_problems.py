# app/routers/user_problems.py
"""Per-user problem state: bookmarks, notes, and self-rated confidence."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel, Field as PydanticField
from typing import List, Optional

from app.database import get_session
from app.models import DSAProblem, DSATopic, UserBookmark, UserNote, UserProblemProgress
from app.routers.auth import get_current_user, User

router = APIRouter(tags=["User Problem State"])


# --- Pydantic Schemas ---
class NoteUpdate(BaseModel):
    content: str = PydanticField(max_length=20_000)


class ConfidenceUpdate(BaseModel):
    confidence: int = PydanticField(ge=1, le=5)


class UserProblemState(BaseModel):
    bookmarked: bool
    note: Optional[str] = None
    confidence: Optional[int] = None


# --- Helpers ---
def _require_problem(session: Session, problem_id: int) -> DSAProblem:
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    return problem


# --- Endpoints ---
@router.get("/problems/{problem_id}/user-state", response_model=UserProblemState)
def get_user_state(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bookmark/note/confidence state for the current user on one problem."""
    _require_problem(session, problem_id)
    bookmark = session.exec(
        select(UserBookmark).where(
            UserBookmark.user_id == current_user.id,
            UserBookmark.problem_id == problem_id,
        )
    ).first()
    note = session.exec(
        select(UserNote).where(
            UserNote.user_id == current_user.id, UserNote.problem_id == problem_id
        )
    ).first()
    progress = session.exec(
        select(UserProblemProgress).where(
            UserProblemProgress.user_id == current_user.id,
            UserProblemProgress.problem_id == problem_id,
        )
    ).first()
    return UserProblemState(
        bookmarked=bookmark is not None,
        note=note.content if note else None,
        confidence=progress.confidence if progress else None,
    )


@router.post("/problems/{problem_id}/bookmark")
def toggle_bookmark(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle a bookmark on a problem."""
    _require_problem(session, problem_id)
    existing = session.exec(
        select(UserBookmark).where(
            UserBookmark.user_id == current_user.id,
            UserBookmark.problem_id == problem_id,
        )
    ).first()
    if existing:
        session.delete(existing)
        session.commit()
        return {"bookmarked": False}
    session.add(UserBookmark(user_id=current_user.id, problem_id=problem_id))
    session.commit()
    return {"bookmarked": True}


@router.put("/problems/{problem_id}/note")
def upsert_note(
    problem_id: int,
    payload: NoteUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create or update the user's note for a problem; empty content deletes it."""
    _require_problem(session, problem_id)
    note = session.exec(
        select(UserNote).where(
            UserNote.user_id == current_user.id, UserNote.problem_id == problem_id
        )
    ).first()

    content = payload.content.strip()
    if not content:
        if note:
            session.delete(note)
            session.commit()
        return {"note": None}

    if note:
        note.content = content
        note.updated_on = datetime.utcnow()
    else:
        note = UserNote(user_id=current_user.id, problem_id=problem_id, content=content)
    session.add(note)
    session.commit()
    return {"note": content}


@router.put("/problems/{problem_id}/confidence")
def set_confidence(
    problem_id: int,
    payload: ConfidenceUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Set the user's self-rated confidence (1-5) for a problem."""
    _require_problem(session, problem_id)
    progress = session.exec(
        select(UserProblemProgress).where(
            UserProblemProgress.user_id == current_user.id,
            UserProblemProgress.problem_id == problem_id,
        )
    ).first()
    if progress:
        progress.confidence = payload.confidence
        progress.updated_on = datetime.utcnow()
    else:
        progress = UserProblemProgress(
            user_id=current_user.id,
            problem_id=problem_id,
            confidence=payload.confidence,
        )
    session.add(progress)
    session.commit()
    return {"confidence": payload.confidence}


@router.get("/me/bookmarks")
def list_bookmarks(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """All problems the user has bookmarked, newest first."""
    rows = session.exec(
        select(UserBookmark, DSAProblem)
        .join(DSAProblem, UserBookmark.problem_id == DSAProblem.id)
        .where(UserBookmark.user_id == current_user.id)
        .order_by(UserBookmark.created_on.desc())
    ).all()

    # Resolve topic names in a single query instead of one SELECT per bookmark.
    topic_ids = {problem.topic_id for _, problem in rows}
    topic_names: dict[int, str] = {}
    if topic_ids:
        topics = session.exec(select(DSATopic).where(DSATopic.id.in_(topic_ids))).all()
        topic_names = {t.id: t.name for t in topics}

    return [
        {
            "id": problem.id,
            "title": problem.title,
            "difficulty": problem.difficulty,
            "topic": topic_names.get(problem.topic_id, "General"),
            "bookmarked_on": bookmark.created_on,
        }
        for bookmark, problem in rows
    ]
