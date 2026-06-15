# app/routers/problem_import.py
"""Admin-only endpoints for the automated problem-import pipeline.

Manual run trigger, run history, coverage status, the review queue, and
publish/archive/regenerate actions. Every route requires admin; `run` and
`upload` are additionally rate-limited (each run can spend AI tokens).
"""

import csv
import io
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import (
    DSAPattern,
    DSAProblem,
    DSATopic,
    ProblemImportRun,
)
from app.routers.auth import require_admin, User
from app.services.ai_service import AIGenerationError, AIUnavailableError
from app.services.problem_import import ai_content
from app.services.problem_import.ranking import coverage_snapshot
from app.services.problem_import.runner import run_import
from app.services.problem_import.sources import (
    AIGeneratedSource,
    CuratedListSource,
    LeetCodeMetadataSource,
    ManualUploadSource,
)
from app.services.rate_limit import RateLimiter

router = APIRouter(prefix="/admin/problem-import", tags=["Problem Import (Admin)"])

logger = logging.getLogger(__name__)

# A run can trigger AI generation + network calls, so throttle bursts.
run_limiter = RateLimiter("problem_import_run", limit=5, window_seconds=60)
upload_limiter = RateLimiter("problem_import_upload", limit=10, window_seconds=60)

_REVIEW_STATUSES = {"review_required", "published", "archived"}
_KNOWN_SOURCES = {"blind75", "grind75", "ai", "leetcode"}


# --- Schemas ---
class RunImportRequest(BaseModel):
    # Subset of source keys; omit/empty = the safe default daily set.
    sources: Optional[List[str]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=100)


class ManualEntry(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    difficulty: str = Field(max_length=20)
    topic: str = Field(min_length=1, max_length=60)
    slug: Optional[str] = Field(default=None, max_length=255)
    url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=20_000)
    interview_frequency_score: Optional[float] = None


class ManualImportRequest(BaseModel):
    entries: List[ManualEntry] = Field(default_factory=list, max_length=200)
    csv_text: Optional[str] = Field(default=None, max_length=100_000)


def _ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AIUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    logger.error("AI generation failed: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI content could not be generated right now. Please try again.",
    )


def _build_sources(keys: Optional[List[str]]):
    if not keys:
        from app.services.problem_import.sources import default_daily_sources

        return default_daily_sources()
    mapping = {
        "blind75": lambda: CuratedListSource("blind75"),
        "grind75": lambda: CuratedListSource("grind75"),
        "ai": AIGeneratedSource,
        "leetcode": LeetCodeMetadataSource,
    }
    sources = []
    for key in keys:
        factory = mapping.get(key)
        if not factory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown source {key!r}. Allowed: {sorted(_KNOWN_SOURCES)}",
            )
        sources.append(factory())
    return sources


# --- Endpoints ---
@router.post(
    "/run", response_model=ProblemImportRun, dependencies=[Depends(run_limiter)]
)
def trigger_run(
    req: RunImportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Run the import pipeline now (manual admin trigger)."""
    sources = _build_sources(req.sources)
    return run_import(
        session,
        trigger="manual",
        sources=sources,
        created_by=current_user.id,
        daily_limit=req.limit,
    )


@router.get("/runs", response_model=List[ProblemImportRun])
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Most recent import runs, newest first."""
    return session.exec(
        select(ProblemImportRun).order_by(ProblemImportRun.id.desc()).limit(limit)
    ).all()


@router.get("/status")
def import_status(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Latest run + per-category coverage snapshot + review-queue size."""
    latest = session.exec(
        select(ProblemImportRun).order_by(ProblemImportRun.id.desc()).limit(1)
    ).first()
    pending = len(
        session.exec(
            select(DSAProblem.id).where(DSAProblem.import_status == "review_required")
        ).all()
    )
    return {
        "latest_run": latest,
        "coverage": coverage_snapshot(session),
        "review_queue_count": pending,
        "ai_enabled": settings.PROBLEM_IMPORT_AI_ENABLED,
        "leetcode_enabled": settings.PROBLEM_IMPORT_LEETCODE_ENABLED,
        "daily_limit": settings.PROBLEM_IMPORT_DAILY_LIMIT,
    }


@router.get("/problems", response_model=List[DSAProblem])
def list_imported_problems(
    import_status: str = Query("review_required"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """List problems by import_status (default the review queue)."""
    if import_status not in _REVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"import_status must be one of {sorted(_REVIEW_STATUSES)}",
        )
    return session.exec(
        select(DSAProblem)
        .where(DSAProblem.import_status == import_status)
        .order_by(DSAProblem.learning_priority_score.desc(), DSAProblem.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


def _set_status(session: Session, problem_id: int, new_status: str) -> DSAProblem:
    from datetime import datetime

    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    problem.import_status = new_status
    problem.updated_on = datetime.utcnow()
    session.add(problem)
    session.commit()
    session.refresh(problem)
    return problem


@router.post("/problems/{problem_id}/publish", response_model=DSAProblem)
def publish_problem(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Make a reviewed problem visible in the public catalog."""
    return _set_status(session, problem_id, "published")


@router.post("/problems/{problem_id}/archive", response_model=DSAProblem)
def archive_problem(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Hide an imported problem (kept for history, excluded from the catalog)."""
    return _set_status(session, problem_id, "archived")


@router.post(
    "/problems/{problem_id}/regenerate-pack",
    dependencies=[Depends(run_limiter)],
)
def regenerate_learning_pack(
    problem_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Generate (and cache) an original AI learning pack for a problem."""
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    topic = session.get(DSATopic, problem.topic_id)
    pattern = session.get(DSAPattern, problem.pattern_id)
    try:
        return ai_content.get_or_create_learning_pack(
            session,
            problem,
            topic.name if topic else "",
            pattern.name if pattern else "",
            force=True,
        )
    except (AIUnavailableError, AIGenerationError) as exc:
        raise _ai_error(exc)


def _parse_csv(csv_text: str) -> List[ManualEntry]:
    reader = csv.DictReader(io.StringIO(csv_text))
    entries: List[ManualEntry] = []
    for row in reader:
        if not row.get("title"):
            continue
        score = row.get("interview_frequency_score")
        entries.append(
            ManualEntry(
                title=row["title"].strip(),
                difficulty=(row.get("difficulty") or "").strip(),
                topic=(row.get("topic") or "").strip(),
                slug=(row.get("slug") or "").strip() or None,
                url=(row.get("url") or "").strip() or None,
                interview_frequency_score=float(score) if score else None,
            )
        )
        if len(entries) >= 200:
            break
    return entries


@router.post(
    "/upload", response_model=ProblemImportRun, dependencies=[Depends(upload_limiter)]
)
def upload_problems(
    req: ManualImportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Import a validated, deduplicated curated list from JSON entries or CSV text."""
    entries = list(req.entries)
    if req.csv_text:
        try:
            entries.extend(_parse_csv(req.csv_text))
        except (csv.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse CSV: {exc}",
            )
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one entry (JSON entries[] or csv_text).",
        )
    source = ManualUploadSource([e.model_dump() for e in entries])
    return run_import(
        session,
        trigger="manual",
        sources=[source],
        created_by=current_user.id,
        daily_limit=len(entries),
    )
