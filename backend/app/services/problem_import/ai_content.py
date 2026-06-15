"""Original AI learning content for imported problems.

Two jobs:
  * ``generate_practice_problem`` — a brand-new, original practice problem for a
    topic (used by AIGeneratedSource), statement + learning pack in one call.
  * ``get_or_create_learning_pack`` — an original explanation/approach/pseudocode/
    hints pack for ANY problem, cached in ``ai_generated_content`` (kind
    ``learning_pack``) so it is generated once and never re-billed on reopen.

All model output is validated with Pydantic before persistence. On any failure we
raise (honest error) rather than store placeholder content.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from app.config import settings
from app.models import AIGeneratedContent, DSAProblem
from app.services.ai_service import (
    AIGenerationError,
    _generate_json,
    ai_available,
)

logger = logging.getLogger(__name__)

LEARNING_PACK_KIND = "learning_pack"

_VALID_DIFFICULTY = {"Easy", "Medium", "Hard"}


class _TestCase(BaseModel):
    input: str
    expected_output: str


class LearningPack(BaseModel):
    explanation: str
    approach: str
    pseudocode: str
    hints: list[str] = Field(default_factory=list)
    time_complexity: str
    space_complexity: str
    beginner_notes: str
    test_cases: list[_TestCase] = Field(default_factory=list)


class _PracticeProblem(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    difficulty: str
    description: str = Field(min_length=20)
    constraints: Optional[str] = None
    examples: list[dict] = Field(default_factory=list)
    starter_code: Optional[str] = None
    learning_pack: LearningPack


_RULES = (
    "You are a DSA curriculum author for the AlgoLens AI learning platform. "
    "Write ONLY original content — never copy or paraphrase LeetCode, GeeksforGeeks, "
    "or any third-party problem statement, editorial, or solution. Be technically "
    "accurate. Audience: a learner who knows basic Python. Respond ONLY with valid "
    "JSON matching the requested schema — no markdown fences, no prose outside JSON."
)

_LEARNING_PACK_SCHEMA = (
    "{\n"
    '  "explanation": "2-4 sentences: what the problem really asks, in plain language",\n'
    '  "approach": "the key insight, then the optimized approach in a short paragraph",\n'
    '  "pseudocode": "newline-separated pseudocode of the optimized approach, max 12 lines",\n'
    '  "hints": ["3-4 progressive hints, least to most revealing"],\n'
    '  "time_complexity": "O(...)",\n'
    '  "space_complexity": "O(...)",\n'
    '  "beginner_notes": "1-3 sentences of encouragement + the core pattern to remember",\n'
    '  "test_cases": [{"input": "string", "expected_output": "string"}]\n'
    "}"
)


def generate_practice_problem(category: str) -> dict[str, Any]:
    """Generate one ORIGINAL beginner/intermediate practice problem for a topic."""
    prompt = (
        f"{_RULES}\n\n"
        f"Create ONE original, beginner-to-intermediate practice problem for the "
        f"DSA topic: {category}. It must be your own invention, not a known problem. "
        "Return JSON with EXACTLY these keys:\n"
        "{\n"
        '  "title": "a short original title (not an existing LeetCode title)",\n'
        '  "difficulty": "Easy" | "Medium" | "Hard",\n'
        '  "description": "the full original problem statement",\n'
        '  "constraints": "input constraints, newline-separated",\n'
        '  "examples": [{"input": "string", "output": "string", "explanation": "string"}],\n'
        '  "starter_code": "a Python function signature with a pass body",\n'
        f'  "learning_pack": {_LEARNING_PACK_SCHEMA}\n'
        "}"
    )
    data = _generate_json(prompt, temperature=0.6)
    try:
        validated = _PracticeProblem(**data)
    except ValidationError as exc:
        raise AIGenerationError(f"Practice problem failed validation: {exc}") from exc
    if validated.difficulty not in _VALID_DIFFICULTY:
        validated.difficulty = "Easy"
    return validated.model_dump()


def generate_learning_pack(
    problem: DSAProblem, topic_name: str = "", pattern_name: str = ""
) -> dict[str, Any]:
    """Generate an original learning pack for an existing problem."""
    context = (
        f"Problem title: {problem.title}\n"
        f"Difficulty: {problem.difficulty}\n"
        f"Topic: {topic_name or 'unknown'}\n"
        f"Pattern: {pattern_name or 'unknown'}\n"
    )
    # For metadata-only problems the stored description is our neutral placeholder,
    # so we lean on the title/topic and instruct the model accordingly.
    prompt = (
        f"{_RULES}\n\n{context}\n"
        "Write an original learning pack for this problem (infer the standard "
        "problem from the title/topic; do NOT reproduce any third-party statement). "
        f"Return JSON with EXACTLY these keys:\n{_LEARNING_PACK_SCHEMA}"
    )
    data = _generate_json(prompt)
    try:
        validated = LearningPack(**data)
    except ValidationError as exc:
        raise AIGenerationError(f"Learning pack failed validation: {exc}") from exc
    return validated.model_dump()


def _get_cached_pack(session: Session, problem_id: int) -> AIGeneratedContent | None:
    return session.exec(
        select(AIGeneratedContent).where(
            AIGeneratedContent.problem_id == problem_id,
            AIGeneratedContent.kind == LEARNING_PACK_KIND,
        )
    ).first()


def persist_learning_pack(
    session: Session, problem_id: int, pack: dict[str, Any]
) -> AIGeneratedContent:
    """Upsert the learning pack cache for a problem and return the row."""
    row = _get_cached_pack(session, problem_id)
    if row:
        row.content = pack
        row.model = settings.GEMINI_MODEL
    else:
        row = AIGeneratedContent(
            problem_id=problem_id,
            kind=LEARNING_PACK_KIND,
            content=pack,
            model=settings.GEMINI_MODEL,
        )
        session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_or_create_learning_pack(
    session: Session,
    problem: DSAProblem,
    topic_name: str = "",
    pattern_name: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Return the cached learning pack, generating + caching it once if absent.

    ``force=True`` regenerates (admin "regenerate" action). Raises the underlying
    AI error if generation fails — never returns placeholder content.
    """
    if not force:
        cached = _get_cached_pack(session, problem.id)
        if cached:
            return {**cached.content, "cached": True}

    if not ai_available():
        from app.services.ai_service import AIUnavailableError

        raise AIUnavailableError(
            "AI features are disabled. Set GOOGLE_GEMINI_API_KEY in backend/.env."
        )
    pack = generate_learning_pack(problem, topic_name, pattern_name)
    persist_learning_pack(session, problem.id, pack)
    return {**pack, "cached": False}
