# app/routers/problems.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
import urllib.parse

from app.database import get_session
from app.models import DSAProblem
from app.routers.auth import require_admin, User

router = APIRouter(prefix="/problems", tags=["Problems"])

# Caps the worst-case response so an unauthenticated catalog read can never pull
# the entire table in one request.
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200


# --- Pydantic Schemas ---
class ProblemCreate(BaseModel):
    title: str
    difficulty: str
    topic_id: int
    pattern_id: int
    description: str
    constraints_text: Optional[str] = None
    starter_code: Optional[str] = None
    leetcode_url: Optional[str] = None


class LeetCodeImportRequest(BaseModel):
    url: str
    topic_id: int
    pattern_id: int
    difficulty: str


# --- Endpoints ---
@router.get("", response_model=List[DSAProblem])
def get_problems(
    topic_id: Optional[int] = None,
    pattern_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Retrieve list of DSA problems, with optional filters and pagination.

    Results are ordered by id and bounded by `limit` (max 200) so a single
    request can never stream the whole table."""
    statement = select(DSAProblem).where(DSAProblem.is_active == True)  # noqa: E712
    if topic_id:
        statement = statement.where(DSAProblem.topic_id == topic_id)
    if pattern_id:
        statement = statement.where(DSAProblem.pattern_id == pattern_id)
    if difficulty:
        statement = statement.where(DSAProblem.difficulty == difficulty)

    statement = statement.order_by(DSAProblem.id).offset(offset).limit(limit)
    return session.exec(statement).all()


@router.get("/{problem_id}", response_model=DSAProblem)
def get_problem(problem_id: int, session: Session = Depends(get_session)):
    """Retrieve detailed information about a single problem"""
    problem = session.get(DSAProblem, problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        )
    return problem


@router.post("", response_model=DSAProblem, status_code=status.HTTP_201_CREATED)
def create_problem(
    problem_data: ProblemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Create a new problem (admin only)"""
    new_problem = DSAProblem(
        title=problem_data.title,
        difficulty=problem_data.difficulty,
        topic_id=problem_data.topic_id,
        pattern_id=problem_data.pattern_id,
        description=problem_data.description,
        constraints_text=problem_data.constraints_text,
        starter_code=problem_data.starter_code,
        leetcode_url=problem_data.leetcode_url,
    )
    if problem_data.leetcode_url:
        # Simple extraction of slug from URL: e.g. https://leetcode.com/problems/two-sum/
        parsed_url = urllib.parse.urlparse(problem_data.leetcode_url)
        path_parts = [p for p in parsed_url.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] == "problems":
            new_problem.leetcode_slug = path_parts[1]

    session.add(new_problem)
    session.commit()
    session.refresh(new_problem)
    return new_problem


@router.post("/import-leetcode-url", response_model=DSAProblem)
def import_leetcode_url(
    req: LeetCodeImportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Import a problem using LeetCode URL, check if exists, otherwise create a placeholder (admin only)"""
    # Extract slug
    parsed_url = urllib.parse.urlparse(req.url)
    path_parts = [p for p in parsed_url.path.split("/") if p]
    slug = None
    if len(path_parts) >= 2 and path_parts[0] == "problems":
        slug = path_parts[1]

    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid LeetCode URL format. Expected: https://leetcode.com/problems/slug-name/",
        )

    # Check if exists
    statement = select(DSAProblem).where(DSAProblem.leetcode_slug == slug)
    existing = session.exec(statement).first()
    if existing:
        return existing

    # Create new placeholder problem
    # Title capitalized from slug
    title = slug.replace("-", " ").title()
    placeholder = DSAProblem(
        title=title,
        leetcode_slug=slug,
        leetcode_url=req.url,
        difficulty=req.difficulty,
        topic_id=req.topic_id,
        pattern_id=req.pattern_id,
        description=f"Placeholder description for {title}. Click standard LeetCode link or use AI generator to create full logic explanations.",
        constraints_text="Constraints will be filled upon AI explanation generation.",
    )
    session.add(placeholder)
    session.commit()
    session.refresh(placeholder)
    return placeholder
