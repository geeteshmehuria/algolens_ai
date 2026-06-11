# app/routers/topic_notes.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any

from app.database import get_session
from app.models import (
    User,
    DSATopic,
    TopicNote,
    TopicQuizQuestion,
    UserQuizAttempt,
    UserTopicNoteState,
    AINoteGenerationLog,
)
from app.routers.auth import get_current_user, require_admin, get_user_role_names
from app.services.note_service import (
    generate_topic_notes,
    generate_topic_quiz,
    grade_quiz_submission,
)
from app.services.ai_service import AIGenerationError, AIUnavailableError
from pydantic import BaseModel

router = APIRouter(tags=["Topic Notes"])

# --- Request Schemas ---

class ProgressUpdate(BaseModel):
    section_key: Optional[str] = None
    completed: Optional[bool] = None
    status: Optional[str] = None


class ChecklistUpdate(BaseModel):
    key: str
    checked: bool


class PersonalNoteUpdate(BaseModel):
    content: str


class QuizSubmitAnswer(BaseModel):
    question_id: int
    answer: str


class QuizSubmission(BaseModel):
    answers: List[QuizSubmitAnswer]


class PatchNoteRequest(BaseModel):
    level: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


# --- Endpoints ---

@router.get("/topics/{topic_id}/notes")
def get_topic_note(
    topic_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve published note (or latest draft for admins/creator) + state."""
    # Find published note
    published_note = session.exec(
        select(TopicNote)
        .where(TopicNote.topic_id == topic_id)
        .where(TopicNote.status == "published")
    ).first()

    note = published_note
    is_preview = False

    user_roles = get_user_role_names(session, current_user.id)
    is_admin = "admin" in user_roles

    # If no published note, search for latest draft if admin or creator
    if not note:
        latest_draft = session.exec(
            select(TopicNote)
            .where(TopicNote.topic_id == topic_id)
            .order_by(TopicNote.version.desc())
        ).first()

        if latest_draft and (is_admin or latest_draft.created_by == current_user.id):
            note = latest_draft
            is_preview = True

    if not note:
        # Check if topic actually exists before offering generation
        topic = session.get(DSATopic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return {"can_generate": True, "detail": "No study notes exist yet for this topic."}

    # Fetch user state for this topic
    state = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(UserTopicNoteState.topic_id == topic_id)
    ).first()

    if not state:
        state = UserTopicNoteState(
            user_id=current_user.id,
            topic_id=topic_id,
            status="reading",
            completed_sections=[],
            checklist_state={},
            is_bookmarked=False,
        )
        session.add(state)
        session.commit()
        session.refresh(state)

    # Return note + state
    return {
        "note": {
            "id": note.id,
            "topic_id": note.topic_id,
            "version": note.version,
            "status": note.status,
            "level": note.level,
            "estimated_reading_minutes": note.estimated_reading_minutes,
            "content": note.content,
            "source": note.source,
            "model": note.model,
            "published_on": note.published_on,
            "is_preview": is_preview,
        },
        "state": state
    }


@router.post("/topics/{topic_id}/notes/generate", status_code=201)
def generate_notes_endpoint(
    topic_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run sequential chunk generation A->B->C, validate, save as draft v1."""
    # Check if a note already exists
    existing = session.exec(
        select(TopicNote).where(TopicNote.topic_id == topic_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Notes already exist for this topic. Use regenerate endpoint instead."
        )

    try:
        note = generate_topic_notes(session, topic_id, current_user.id)
        return {
            "note_id": note.id,
            "topic_id": note.topic_id,
            "version": note.version,
            "status": note.status,
            "estimated_reading_minutes": note.estimated_reading_minutes,
            "generation": {
                "model": note.model,
                "chunks_succeeded": 3,
            }
        }
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except AIGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/topics/{topic_id}/notes/regenerate", status_code=201)
def regenerate_notes_endpoint(
    topic_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Generate new version (v+1) draft (Admin only)."""
    try:
        note = generate_topic_notes(session, topic_id, current_user.id)
        return {
            "note_id": note.id,
            "topic_id": note.topic_id,
            "version": note.version,
            "status": note.status,
            "estimated_reading_minutes": note.estimated_reading_minutes,
            "generation": {
                "model": note.model,
                "chunks_succeeded": 3,
            }
        }
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except AIGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/topics/{topic_id}/notes/versions")
def get_note_versions(
    topic_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """List all versions of a note (Admin only)."""
    versions = session.exec(
        select(TopicNote)
        .where(TopicNote.topic_id == topic_id)
        .order_by(TopicNote.version.desc())
    ).all()
    return [
        {
            "id": v.id,
            "version": v.version,
            "status": v.status,
            "level": v.level,
            "source": v.source,
            "model": v.model,
            "created_on": v.created_on,
            "published_on": v.published_on,
        }
        for v in versions
    ]


@router.get("/topic-notes/{note_id}")
def get_note_by_id(
    note_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of a single topic note by id."""
    note = session.get(TopicNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Topic note not found")

    user_roles = get_user_role_names(session, current_user.id)
    is_admin = "admin" in user_roles
    if note.status != "published" and not is_admin and note.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this draft note.")

    return note


@router.patch("/topic-notes/{note_id}")
def edit_draft_note(
    note_id: int,
    body: PatchNoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Edit content/level of a draft or in_review note (Admin only)."""
    note = session.get(TopicNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Topic note not found")

    if note.status == "published":
        raise HTTPException(
            status_code=409,
            detail="Cannot edit a published note directly. Please regenerate a new version instead."
        )

    if body.level is not None:
        note.level = body.level
    if body.content is not None:
        note.content = body.content

    note.source = "ai_edited"
    note.updated_on = datetime.utcnow()

    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.post("/topic-notes/{note_id}/publish")
def publish_note(
    note_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Mark draft note as published; archives any other published note in same transaction."""
    note = session.get(TopicNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Topic note not found")

    if note.status == "published":
        return {"detail": "Note is already published."}

    # Archive previously published note for this topic
    prev_published = session.exec(
        select(TopicNote)
        .where(TopicNote.topic_id == note.topic_id)
        .where(TopicNote.status == "published")
    ).all()

    for old_note in prev_published:
        old_note.status = "archived"
        session.add(old_note)

    # Publish new note
    note.status = "published"
    note.published_on = datetime.utcnow()
    note.reviewed_by = current_user.id
    note.reviewed_on = datetime.utcnow()
    note.updated_on = datetime.utcnow()

    session.add(note)
    session.commit()
    session.refresh(note)

    return {"detail": f"Note version {note.version} published successfully."}


@router.post("/topics/{topic_id}/notes/bookmark")
def toggle_bookmark(
    topic_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the bookmark state on user_topic_note_state."""
    state = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(UserTopicNoteState.topic_id == topic_id)
    ).first()

    if not state:
        state = UserTopicNoteState(
            user_id=current_user.id,
            topic_id=topic_id,
            status="reading",
            completed_sections=[],
            checklist_state={},
            is_bookmarked=True,
        )
    else:
        state.is_bookmarked = not state.is_bookmarked

    session.add(state)
    session.commit()
    session.refresh(state)
    return {"is_bookmarked": state.is_bookmarked}


@router.put("/topics/{topic_id}/notes/progress")
def update_progress(
    topic_id: int,
    body: ProgressUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update completed sections list or status."""
    state = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(UserTopicNoteState.topic_id == topic_id)
    ).first()

    if not state:
        state = UserTopicNoteState(
            user_id=current_user.id,
            topic_id=topic_id,
            status="reading",
            completed_sections=[],
            checklist_state={},
            is_bookmarked=False,
        )

    if body.status is not None:
        if body.status not in ("reading", "completed", "revised"):
            raise HTTPException(status_code=400, detail="Invalid status")
        state.status = body.status

    if body.section_key is not None and body.completed is not None:
        # Validate section_key against published note actual sections if we can
        published = session.exec(
            select(TopicNote)
            .where(TopicNote.topic_id == topic_id)
            .where(TopicNote.status == "published")
        ).first()

        # Fallback to any latest version draft if no published note
        if not published:
            published = session.exec(
                select(TopicNote)
                .where(TopicNote.topic_id == topic_id)
                .order_by(TopicNote.version.desc())
            ).first()

        if published:
            valid_keys = {s.get("section_key") for s in published.content.get("sections", [])}
            if body.section_key not in valid_keys:
                raise HTTPException(
                    status_code=400,
                    detail=f"Section key '{body.section_key}' not valid for this topic notes."
                )

        completed_set = set(state.completed_sections)
        if body.completed:
            completed_set.add(body.section_key)
        else:
            completed_set.discard(body.section_key)
        state.completed_sections = list(completed_set)

    state.last_read_on = datetime.utcnow()
    session.add(state)
    session.commit()
    session.refresh(state)
    return state


@router.put("/topics/{topic_id}/notes/checklist")
def update_checklist(
    topic_id: int,
    body: ChecklistUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update checklist item confidence."""
    state = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(UserTopicNoteState.topic_id == topic_id)
    ).first()

    if not state:
        state = UserTopicNoteState(
            user_id=current_user.id,
            topic_id=topic_id,
            status="reading",
            completed_sections=[],
            checklist_state={},
            is_bookmarked=False,
        )

    checklist = dict(state.checklist_state or {})
    checklist[body.key] = body.checked
    state.checklist_state = checklist

    session.add(state)
    session.commit()
    session.refresh(state)
    return state


@router.put("/topics/{topic_id}/notes/personal-note")
def update_personal_note(
    topic_id: int,
    body: PersonalNoteUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create or update user's own study notes for the topic. Empty content deletes."""
    state = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(UserTopicNoteState.topic_id == topic_id)
    ).first()

    if not state:
        state = UserTopicNoteState(
            user_id=current_user.id,
            topic_id=topic_id,
            status="reading",
            completed_sections=[],
            checklist_state={},
            is_bookmarked=False,
        )

    content_str = body.content.strip()
    state.personal_notes_md = content_str if content_str else None

    session.add(state)
    session.commit()
    session.refresh(state)
    return state


@router.post("/topic-notes/{note_id}/quiz/generate", status_code=201)
def generate_quiz_endpoint(
    note_id: int,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate quiz questions if none exist."""
    # Check if quiz already exists
    existing = session.exec(
        select(TopicQuizQuestion).where(TopicQuizQuestion.note_id == note_id)
    ).first()

    if existing and not force:
        raise HTTPException(
            status_code=409,
            detail="Quiz already exists for this note version."
        )

    # Delete existing if forcing
    if existing and force:
        user_roles = get_user_role_names(session, current_user.id)
        if "admin" not in user_roles:
            raise HTTPException(
                status_code=403,
                detail="Only admin can force quiz regeneration."
            )
        questions_to_delete = session.exec(
            select(TopicQuizQuestion).where(TopicQuizQuestion.note_id == note_id)
        ).all()
        for q in questions_to_delete:
            session.delete(q)
        session.commit()

    try:
        questions = generate_topic_quiz(session, note_id, current_user.id)
        return {"detail": f"Successfully generated {len(questions)} quiz questions."}
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except AIGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/topic-notes/{note_id}/quiz")
def get_quiz_questions(
    note_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Fetch quiz questions WITHOUT correct answers / explanations."""
    questions = session.exec(
        select(TopicQuizQuestion)
        .where(TopicQuizQuestion.note_id == note_id)
        .order_by(TopicQuizQuestion.position)
    ).all()

    return [
        {
            "id": q.id,
            "position": q.position,
            "kind": q.kind,
            "question": q.question,
            "options": q.options,
        }
        for q in questions
    ]


@router.post("/topic-notes/{note_id}/quiz/submit")
def submit_quiz(
    note_id: int,
    submission: QuizSubmission,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Grade submission server-side and record the attempt."""
    # Validate question ids match this note
    questions = session.exec(
        select(TopicQuizQuestion).where(TopicQuizQuestion.note_id == note_id)
    ).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No quiz questions found for this note.")

    valid_q_ids = {q.id for q in questions}
    payload_answers = []

    for ans in submission.answers:
        if ans.question_id not in valid_q_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Question id {ans.question_id} does not belong to this quiz."
            )
        
        # Validate MCQ options
        q_obj = next(q for q in questions if q.id == ans.question_id)
        if q_obj.kind == "mcq":
            try:
                opt_idx = int(ans.answer)
                if opt_idx < 0 or opt_idx > 3:
                    raise ValueError
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"MCQ answer for question {ans.question_id} must be a 0-based option index ('0'-'3')."
                )

        payload_answers.append({
            "question_id": ans.question_id,
            "answer": ans.answer
        })

    try:
        attempt, results = grade_quiz_submission(
            session, note_id, current_user.id, payload_answers
        )
        return {
            "score": attempt.score,
            "total": attempt.total,
            "results": results
        }
    except AIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/me/topic-notes")
def get_user_topics_list(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all topics + note availability + user state + last quiz score."""
    topics = session.exec(select(DSATopic)).all()

    # Get states
    states = session.exec(
        select(UserTopicNoteState).where(UserTopicNoteState.user_id == current_user.id)
    ).all()
    state_map = {s.topic_id: s for s in states}

    # Get note availability status (whether a published note exists)
    published_notes = session.exec(
        select(TopicNote.topic_id).where(TopicNote.status == "published")
    ).all()
    published_set = set(published_notes)

    # Get all quiz attempts for this user to calculate last quiz score
    attempts = session.exec(
        select(UserQuizAttempt)
        .where(UserQuizAttempt.user_id == current_user.id)
        .order_by(UserQuizAttempt.created_on.desc())
    ).all()

    # Map topic note id -> latest attempt score / total
    # Since attempts link to note_id, we need to map note_id -> topic_id
    notes = session.exec(select(TopicNote.id, TopicNote.topic_id)).all()
    note_to_topic = {n_id: t_id for n_id, t_id in notes}

    last_quiz_score_map = {}
    for att in attempts:
        topic_id = note_to_topic.get(att.note_id)
        if topic_id and topic_id not in last_quiz_score_map:
            last_quiz_score_map[topic_id] = {
                "score": att.score,
                "total": att.total,
                "created_on": att.created_on,
            }

    result = []
    for t in topics:
        state = state_map.get(t.id)
        quiz = last_quiz_score_map.get(t.id)

        result.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "has_published_note": t.id in published_set,
            "state": {
                "status": state.status if state else "reading",
                "is_bookmarked": state.is_bookmarked if state else False,
                "completed_sections_count": len(state.completed_sections) if state else 0,
                "last_read_on": state.last_read_on if state else None,
            } if state else None,
            "last_quiz": quiz
        })

    return result


@router.get("/me/revision-notes")
def get_user_revision_notes(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve only the 'revision_notes' sections of completed or bookmarked topics."""
    # Find all states that are completed or bookmarked
    states = session.exec(
        select(UserTopicNoteState)
        .where(UserTopicNoteState.user_id == current_user.id)
        .where(
            (UserTopicNoteState.status == "completed") |
            (UserTopicNoteState.status == "revised") |
            (UserTopicNoteState.is_bookmarked == True)
        )
    ).all()

    if not states:
        return []

    topic_ids = [s.topic_id for s in states]

    # Fetch published notes for these topics
    notes = session.exec(
        select(TopicNote)
        .where(TopicNote.topic_id.in_(topic_ids))
        .where(TopicNote.status == "published")
    ).all()

    note_map = {n.topic_id: n for n in notes}
    topic_map = {t.id: t for t in session.exec(select(DSATopic).where(DSATopic.id.in_(topic_ids))).all()}

    results = []
    for state in states:
        note = note_map.get(state.topic_id)
        topic = topic_map.get(state.topic_id)
        if not note or not topic:
            continue

        # Extract revision notes section + checklist + plan
        revision_section = None
        for s in note.content.get("sections", []):
            if s.get("section_key") == "revision_notes":
                revision_section = s
                break

        results.append({
            "topic_id": topic.id,
            "topic_name": topic.name,
            "level": note.level,
            "revision_section": revision_section,
            "code_templates": note.content.get("code_templates", []),
            "confidence_checklist": note.content.get("confidence_checklist", []),
            "checklist_state": state.checklist_state,
        })

    return results
