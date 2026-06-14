# app/routers/ai.py
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from app.config import settings
from app.database import get_session
from app.services.rate_limit import RateLimiter
from app.models import (
    DSAProblem,
    DSATopic,
    DSAPattern,
    AIGeneratedContent,
    AIHint,
    AICodeReview,
    ProblemAttempt,
)
from app.routers.auth import get_current_user, User
from app.services import ai_service, step_generators
from app.services.ai_service import AIUnavailableError, AIGenerationError
from app.services.progress_service import schedule_revision

router = APIRouter(prefix="/ai", tags=["Google Gemini AI"])

logger = logging.getLogger(__name__)

# Each call here spends Gemini tokens, so cap per-IP request volume. The cache
# means repeat reads cost nothing; this throttles bursts of fresh generation.
ai_limiter = RateLimiter("ai_generate", limit=20, window_seconds=60)

# Hard ceiling on code we send to the model — also bounds DB row size and cost.
MAX_CODE_CHARS = 20_000


# --- Pydantic Schemas ---
class CodeReviewRequest(BaseModel):
    problem_id: int
    submitted_code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
    used_hint: bool = False


class HintRequest(BaseModel):
    problem_id: int
    hint_level: int = Field(ge=1, le=3)


# --- Helpers ---
def _load_problem(session: Session, problem_id: int) -> tuple[DSAProblem, str, str]:
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    topic = session.get(DSATopic, problem.topic_id)
    pattern = session.get(DSAPattern, problem.pattern_id)
    return problem, (topic.name if topic else ""), (pattern.name if pattern else "")


def _get_cached(
    session: Session, problem_id: int, kind: str
) -> AIGeneratedContent | None:
    return session.exec(
        select(AIGeneratedContent).where(
            AIGeneratedContent.problem_id == problem_id,
            AIGeneratedContent.kind == kind,
        )
    ).first()


def _ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AIUnavailableError):
        # Configuration guidance — safe and useful to show
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    # Provider errors can carry internal details (paths, quotas, stack hints):
    # full detail goes to the server log, the client gets a generic message.
    logger.error("AI generation failed: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI response could not be generated right now. Please try again.",
    )


# --- Endpoints ---
@router.post("/generate-explanation/{problem_id}", dependencies=[Depends(ai_limiter)])
def generate_explanation(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate (or serve cached) AI explanation for a problem.

    The first request per problem hits Gemini; the result is cached in
    ai_generated_content and served to everyone afterwards.
    """
    cached = _get_cached(session, problem_id, "explanation")
    if cached:
        return {**cached.content, "cached": True}

    problem, topic_name, pattern_name = _load_problem(session, problem_id)
    try:
        content = ai_service.generate_explanation(problem, topic_name, pattern_name)
    except (AIUnavailableError, AIGenerationError) as exc:
        raise _ai_error(exc)

    session.add(
        AIGeneratedContent(
            problem_id=problem_id,
            kind="explanation",
            content=content,
            model=settings.GEMINI_MODEL,
        )
    )
    session.commit()
    return {**content, "cached": False}


@router.post("/generate-animation/{problem_id}", dependencies=[Depends(ai_limiter)])
def generate_animation(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate (or serve cached) step-by-step animation data for a problem.

    Patterns with an instrumented algorithm implementation (binary search,
    two pointers, stack) get exact deterministic steps for free; other
    patterns fall back to Gemini. Step JSON follows a per-animation-type
    contract the frontend renders.
    """
    cached = _get_cached(session, problem_id, "animation")
    if cached:
        return {**cached.content, "cached": True}

    problem, topic_name, pattern_name = _load_problem(session, problem_id)

    content = step_generators.generate_for_problem(problem, topic_name, pattern_name)
    model_used = "deterministic"
    if content is None:
        explanation = _get_cached(session, problem_id, "explanation")
        pseudocode = explanation.content.get("pseudocode") if explanation else None
        try:
            content = ai_service.generate_animation(
                problem, topic_name, pattern_name, pseudocode
            )
        except (AIUnavailableError, AIGenerationError) as exc:
            raise _ai_error(exc)
        model_used = settings.GEMINI_MODEL

    session.add(
        AIGeneratedContent(
            problem_id=problem_id,
            kind="animation",
            content=content,
            model=model_used,
        )
    )
    session.commit()
    return {**content, "cached": False}


@router.post("/review-code", dependencies=[Depends(ai_limiter)])
def review_code(
    req: CodeReviewRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Review submitted code with Gemini, persist the review, and update
    the learner's attempt status. A correct solution schedules a spaced
    revision automatically."""
    problem, topic_name, pattern_name = _load_problem(session, req.problem_id)
    try:
        review = ai_service.review_code(
            problem, req.submitted_code, topic_name, pattern_name
        )
    except (AIUnavailableError, AIGenerationError) as exc:
        raise _ai_error(exc)

    # The frontend logs a 'Reviewing' attempt right before requesting the review.
    attempt = session.exec(
        select(ProblemAttempt)
        .where(
            ProblemAttempt.user_id == current_user.id,
            ProblemAttempt.problem_id == req.problem_id,
        )
        .order_by(ProblemAttempt.created_on.desc())
    ).first()

    if attempt:
        attempt.status = "Correct" if review["is_correct"] else "Incorrect"
        attempt.ai_score = review["score"]
        attempt.time_complexity = review.get("time_complexity")
        attempt.space_complexity = review.get("space_complexity")
        session.add(attempt)
        session.add(
            AICodeReview(
                attempt_id=attempt.id,
                is_correct=review["is_correct"],
                logic_feedback=review["logic_feedback"],
                bugs=review["bugs"],
                missed_edge_cases=review["missed_edge_cases"],
                better_approach=review.get("better_approach"),
                dsa_pattern=review.get("dsa_pattern"),
                time_complexity=review.get("time_complexity"),
                space_complexity=review.get("space_complexity"),
                score=review["score"],
            )
        )
        if review["is_correct"]:
            schedule_revision(
                session, current_user.id, req.problem_id, reason="Solved with AI review"
            )
        session.commit()

    return review


@router.post("/hint", dependencies=[Depends(ai_limiter)])
def get_hint(
    req: HintRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a leveled Socratic hint (1=nudge, 2=pattern, 3=approach).

    Cached per (user, problem, level): once a hint exists it is served from the
    DB so re-requesting the same hint costs zero AI tokens (consistent with the
    shared explanation/animation caching)."""
    problem, topic_name, pattern_name = _load_problem(session, req.problem_id)

    cached = session.exec(
        select(AIHint).where(
            AIHint.user_id == current_user.id,
            AIHint.problem_id == req.problem_id,
            AIHint.hint_level == req.hint_level,
        )
    ).first()
    if cached:
        return {"hint_level": cached.hint_level, "hint_text": cached.hint_text}

    try:
        hint_text = ai_service.generate_hint(
            problem, req.hint_level, topic_name, pattern_name
        )
    except (AIUnavailableError, AIGenerationError) as exc:
        raise _ai_error(exc)

    session.add(
        AIHint(
            user_id=current_user.id,
            problem_id=req.problem_id,
            hint_level=req.hint_level,
            hint_text=hint_text,
        )
    )
    session.commit()

    return {"hint_level": req.hint_level, "hint_text": hint_text}
