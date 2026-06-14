# app/services/note_service.py
import json
import re
import time
import logging
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import BaseModel, Field, field_validator, ValidationError
from sqlmodel import Session, select

from app.config import settings
from app.models import (
    DSATopic,
    TopicNote,
    TopicQuizQuestion,
    UserQuizAttempt,
    AINoteGenerationLog,
)
from app.services.ai_service import ai_available, AIUnavailableError, AIGenerationError

logger = logging.getLogger(__name__)

# --- PYDANTIC SCHEMAS FOR VALIDATION ---


class ProblemInfo(BaseModel):
    title: str
    difficulty: Literal["Easy", "Medium", "Hard"]
    pattern: str
    what_to_learn: str
    leetcode_slug: Optional[str] = None


class NoteSection(BaseModel):
    section_key: str
    title: str
    content_md: str
    examples: List[str] = Field(default=[])
    common_mistakes: List[str] = Field(default=[])
    interview_tips: List[str] = Field(default=[])
    problems: Optional[List[ProblemInfo]] = None


class NotesLearnChunk(BaseModel):
    sections: List[NoteSection]


class PseudocodeTemplate(BaseModel):
    name: str
    when_to_use: str
    pseudocode: str


class LineExplanation(BaseModel):
    lines: str
    explanation: str


class CodeTemplate(BaseModel):
    language: str
    name: str
    code: str
    line_explanations: List[LineExplanation] = Field(default=[])


class ComplexityRow(BaseModel):
    operation: str
    time: str
    space: str
    note: str

    @field_validator("time", "space")
    def validate_complexity_pattern(cls, v):
        if not (v.startswith("O(") and v.endswith(")")):
            raise ValueError(f"Complexity must match pattern O(...), got '{v}'")
        return v


class ComplexityNotes(BaseModel):
    table: List[ComplexityRow]
    how_to_derive: str
    common_mistakes: List[str] = Field(default=[])


class NotesApplyChunk(BaseModel):
    sections: List[NoteSection]
    pseudocode_templates: List[PseudocodeTemplate]
    code_templates: List[CodeTemplate]
    complexity_notes: ComplexityNotes


class PracticePlanSevenDay(BaseModel):
    day: int
    focus: str
    tasks: List[str]
    problems: List[ProblemInfo]


class PracticePlan(BaseModel):
    one_day: List[str]
    seven_day: List[PracticePlanSevenDay]


class ConfidenceChecklist(BaseModel):
    key: str
    label: str


class NotesRetainChunk(BaseModel):
    sections: List[NoteSection]
    practice_plan: PracticePlan
    confidence_checklist: List[ConfidenceChecklist]
    estimated_reading_minutes: int
    level: str

    @field_validator("confidence_checklist")
    def validate_checklist_keys_unique(cls, v):
        keys = [item.key for item in v]
        if len(keys) != len(set(keys)):
            raise ValueError("confidence_checklist keys must be unique")
        return v


class QuizQuestionInput(BaseModel):
    kind: Literal["mcq", "short_answer", "dry_run", "complexity"]
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    answer_explanation: str

    @field_validator("options")
    def validate_options_for_mcq(cls, v, info):
        if info.data.get("kind") == "mcq":
            if not v or len(v) != 4:
                raise ValueError("MCQ questions must have exactly 4 options")
        return v


class QuizInput(BaseModel):
    questions: List[QuizQuestionInput]


# --- GEMINI CLIENT WRAPPER ---

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
    return _client


def _call_gemini_with_usage(
    prompt: str, temperature: float = 0.3
) -> Tuple[Dict[str, Any], int, int, int]:
    """Calls Gemini and returns (parsed_json, input_tokens, output_tokens, latency_ms)"""
    if not ai_available():
        raise AIUnavailableError(
            "AI features are disabled. Set GOOGLE_GEMINI_API_KEY in backend/.env."
        )

    t0 = time.time()
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": temperature,
            },
        )
        latency_ms = int((time.time() - t0) * 1000)
        text = response.text or ""
    except Exception as exc:
        raise AIGenerationError(f"Gemini request failed: {exc}") from exc

    # Parse and strip md fences
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIGenerationError(f"Gemini returned invalid JSON: {text[:200]}") from exc

    # Retrieve usage metadata
    input_tokens = 0
    output_tokens = 0
    if response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    return data, input_tokens, output_tokens, latency_ms


# --- SHARED SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    "You are a senior interview coach writing study notes for a DSA learning platform. "
    "Audience: a learner preparing for software-engineering interviews who knows basic Python. "
    "Be deep and practical, never generic — every claim must be concrete enough to act on. "
    "Use original wording only; never reproduce text from LeetCode or other sites. "
    "When referencing well-known problems, give the common problem NAME and a one-line original description — never the full statement. "
    "Respond ONLY with valid JSON matching the requested schema. All prose fields are GitHub-flavored markdown.\n"
)


# --- CORE NOTES GENERATION SERVICE ---


def generate_topic_notes(
    session: Session,
    topic_id: int,
    user_id: Optional[int],
    level: str = "beginner_to_intermediate",
) -> TopicNote:
    """Sequential chunk-by-chunk generator with retry-once capability."""
    topic = session.get(DSATopic, topic_id)
    if not topic:
        raise ValueError(f"DSA Topic with id {topic_id} not found.")

    pattern_names = ", ".join([p.name for p in topic.patterns])

    # Context variables
    topic_name = topic.name
    topic_description = topic.description or ""

    # 1. Chunk A: Learn
    chunk_a_prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Topic: {topic_name}\n"
        f"Topic description from our platform: {topic_description}\n"
        f"Target level: {level}\n"
        f"Patterns we teach under this topic: {pattern_names}\n\n"
        "Write the LEARNING half of the study notes. Return JSON matching this schema:\n"
        "{\n"
        '  "sections": [\n'
        '    {"section_key": "overview", "title": "Overview", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "core_concepts", "title": "Core Concepts", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "visual_walkthrough", "title": "Visual Walkthrough", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "interview_patterns", "title": "Interview Patterns", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "roadmap", "title": "Roadmap", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []}\n'
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- overview: what it is, why interviews love it, one real-world analogy, 150-250 words.\n"
        "- core_concepts: definitions, key operations, when to use vs NOT use. Use markdown tables where natural.\n"
        "- visual_walkthrough: ONE small concrete example traced step by step in numbered steps, showing pointer/stack/table state at each step as inline code.\n"
        "- interview_patterns: each pattern with the KEYWORDS in a problem statement that signal it.\n"
        "- roadmap: ordered list, each item = concept + why it comes at that position.\n"
        "- Every section MUST have >= 2 common_mistakes and >= 1 interview_tip.\n"
    )

    data_a, in_a, out_a, lat_a = _call_chunk_with_retry(
        "notes_learn", chunk_a_prompt, NotesLearnChunk, topic_id, user_id, session
    )

    # 2. Chunk B: Apply
    chunk_b_prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Topic: {topic_name}\n"
        f"Topic description from our platform: {topic_description}\n"
        f"Target level: {level}\n"
        f"Patterns we teach under this topic: {pattern_names}\n\n"
        "Write the APPLICATION half. Return JSON matching this schema:\n"
        "{\n"
        '  "sections": [\n'
        '    {"section_key": "practice_problems", "title": "Problems Worth Doing", "content_md": "...",\n'
        '     "problems": [{"title": "...", "difficulty": "Easy|Medium|Hard", "pattern": "...", "what_to_learn": "...", "leetcode_slug": "kebab-case-or-null"}],\n'
        '     "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "edge_cases", "title": "Edge Cases to Watch", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []},\n'
        '    {"section_key": "interview_script", "title": "Interview Script", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []}\n'
        "  ],\n"
        '  "pseudocode_templates": [{"name": "...", "when_to_use": "...", "pseudocode": "..."}],\n'
        '  "code_templates": [{"language": "python", "name": "...", "code": "...", "line_explanations": [{"lines": "3-5", "explanation": "..."}]}],\n'
        '  "complexity_notes": {"table": [{"operation": "...", "time": "...", "space": "...", "note": "..."}], "how_to_derive": "...", "common_mistakes": ["..."]}\n'
        "}\n"
        "Rules:\n"
        "- practice_problems: 3-4 Easy, 3-4 Medium, 2 Hard problems. leetcode_slug only if you are CERTAIN of the canonical slug; otherwise null. NEVER invent URLs.\n"
        "- interview_script: literal first-person sentences the learner can say out loud, covering clarifying questions, brute force first, the optimization insight, complexity statement.\n"
        "- code_templates: Python required; JavaScript only when the topic is genuinely common in JS interviews.\n"
        "- Every complexity value must match the pattern O(...).\n"
    )

    data_b, in_b, out_b, lat_b = _call_chunk_with_retry(
        "notes_apply", chunk_b_prompt, NotesApplyChunk, topic_id, user_id, session
    )

    # 3. Chunk C: Retain
    chunk_c_prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Topic: {topic_name}\n"
        f"Topic description from our platform: {topic_description}\n"
        f"Target level: {level}\n"
        f"Patterns we teach under this topic: {pattern_names}\n\n"
        "Write the RETENTION pack. Return JSON matching this schema:\n"
        "{\n"
        '  "sections": [{"section_key": "revision_notes", "title": "Last-Minute Revision", "content_md": "...", "examples": [], "common_mistakes": [], "interview_tips": []}],\n'
        '  "practice_plan": {"one_day": ["..."], "seven_day": [{"day": 1, "focus": "...", "tasks": ["..."], "problems": [{"title": "...", "difficulty": "...", "pattern": "...", "what_to_learn": "...", "leetcode_slug": null}]}]},\n'
        '  "confidence_checklist": [{"key": "snake_case_key", "label": "I can ..."}],\n'
        '  "estimated_reading_minutes": 18,\n'
        '  "level": "beginner_to_intermediate"\n'
        "}\n"
        "Rules:\n"
        "- revision_notes: scannable in under 3 minutes — bullet fragments, formulas, template names, top-5 mistakes.\n"
        '- checklist: 5-8 items, each independently verifiable by the learner ("I can write X from scratch"), ordered easy -> hard. Keys must be unique snake_case.\n'
        "- seven_day plan: max 2 problems/day, at least one lighter consolidation day.\n"
    )

    data_c, in_c, out_c, lat_c = _call_chunk_with_retry(
        "notes_retain", chunk_c_prompt, NotesRetainChunk, topic_id, user_id, session
    )

    # Determine version (v+1)
    existing_versions = session.exec(
        select(TopicNote.version)
        .where(TopicNote.topic_id == topic_id)
        .order_by(TopicNote.version.desc())
    ).all()
    next_version = (existing_versions[0] + 1) if existing_versions else 1

    # Assemble final content JSON
    merged_sections = data_a["sections"] + data_b["sections"] + data_c["sections"]
    content = {
        "sections": merged_sections,
        "pseudocode_templates": data_b["pseudocode_templates"],
        "code_templates": data_b["code_templates"],
        "complexity_notes": data_b["complexity_notes"],
        "practice_plan": data_c["practice_plan"],
        "confidence_checklist": data_c["confidence_checklist"],
    }

    # Save to db
    topic_note = TopicNote(
        topic_id=topic_id,
        version=next_version,
        status="draft",
        level=level,
        estimated_reading_minutes=data_c["estimated_reading_minutes"],
        schema_version=1,
        content=content,
        source="ai",
        model=settings.GEMINI_MODEL,
        created_by=user_id,
    )
    session.add(topic_note)
    session.commit()
    session.refresh(topic_note)

    return topic_note


def _call_chunk_with_retry(
    kind: str,
    prompt: str,
    schema_cls: Any,
    topic_id: int,
    user_id: Optional[int],
    session: Session,
) -> Tuple[Dict[str, Any], int, int, int]:
    """Helper to run model call and retry once if validation fails."""
    try:
        data, in_tokens, out_tokens, latency = _call_gemini_with_usage(prompt)
        schema_cls.model_validate(data)

        # Log success
        _log_generation(
            session, topic_id, user_id, kind, True, None, in_tokens, out_tokens, latency
        )
        return data, in_tokens, out_tokens, latency
    except (AIGenerationError, ValidationError) as exc:
        logger.warning(
            f"First attempt failed for chunk {kind}. Error: {exc}. Retrying..."
        )

        # Build correction prompt
        retry_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Your previous response failed schema validation with error: {exc}.\n"
            "Return corrected valid JSON only."
        )
        try:
            data, in_tokens, out_tokens, latency = _call_gemini_with_usage(retry_prompt)
            schema_cls.model_validate(data)

            # Log success on retry
            _log_generation(
                session,
                topic_id,
                user_id,
                kind,
                True,
                None,
                in_tokens,
                out_tokens,
                latency,
            )
            return data, in_tokens, out_tokens, latency
        except Exception as retry_exc:
            # Log failure
            _log_generation(
                session, topic_id, user_id, kind, False, str(retry_exc), 0, 0, 0
            )
            raise AIGenerationError(
                f"Generation of chunk '{kind}' failed twice. Last error: {retry_exc}"
            ) from retry_exc


def _log_generation(
    session: Session,
    topic_id: int,
    user_id: Optional[int],
    kind: str,
    success: bool,
    error: Optional[str],
    in_tok: int,
    out_tok: int,
    latency: int,
):
    log = AINoteGenerationLog(
        topic_id=topic_id,
        user_id=user_id,
        kind=kind,
        model=settings.GEMINI_MODEL,
        success=success,
        error=error,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency,
    )
    session.add(log)
    session.commit()


# --- QUIZ GENERATION AND GRADING ---


def generate_topic_quiz(
    session: Session, note_id: int, user_id: Optional[int]
) -> List[TopicQuizQuestion]:
    """Generates quiz questions for a topic note and inserts them into DB."""
    note = session.get(TopicNote, note_id)
    if not note:
        raise ValueError(f"TopicNote with id {note_id} not found.")

    topic = session.get(DSATopic, note.topic_id)
    topic_name = topic.name if topic else "DSA Topic"

    # Gather sections overview for quiz context
    sections_summary = "\n".join(
        [
            f"- {s.get('title', 'Section')}: {s.get('content_md', '')[:200]}..."
            for s in note.content.get("sections", [])
        ]
    )

    prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Topic: {topic_name}\n"
        f"Note overview:\n{sections_summary}\n\n"
        "Create a quiz testing UNDERSTANDING, not trivia. Return JSON matching this schema:\n"
        "{\n"
        '  "questions": [\n'
        '    {"kind": "mcq|short_answer|dry_run|complexity", "question": "...", "options": ["option 0", "option 1", "option 2", "option 3"] or null, "correct_answer": "...", "answer_explanation": "..."}\n'
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- 8-10 questions: 4-5 mcq, 2 complexity, 1-2 short_answer, 1-2 dry_run.\n"
        "- mcq: exactly 4 options, correct_answer is the 0-based index AS A STRING (e.g. '1'); distractors must be plausible misconceptions, not jokes.\n"
        "- dry_run: give a tiny concrete input and ask for the state after N steps.\n"
        "- complexity: ask for big-O complexity of a short code snippet or conceptual algorithm.\n"
        "- answer_explanation must teach WHY, not just restate the answer.\n"
    )

    try:
        data, in_tok, out_tok, latency = _call_gemini_with_usage(prompt)
        QuizInput.model_validate(data)

        # Log success
        _log_generation(
            session,
            note.topic_id,
            user_id,
            "quiz",
            True,
            None,
            in_tok,
            out_tok,
            latency,
        )
    except Exception as exc:
        logger.warning(f"Quiz generation failed: {exc}. Retrying...")
        retry_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Your previous response failed schema validation with error: {exc}.\n"
            "Return corrected valid JSON only."
        )
        try:
            data, in_tok, out_tok, latency = _call_gemini_with_usage(retry_prompt)
            QuizInput.model_validate(data)
            _log_generation(
                session,
                note.topic_id,
                user_id,
                "quiz",
                True,
                None,
                in_tok,
                out_tok,
                latency,
            )
        except Exception as retry_exc:
            _log_generation(
                session, note.topic_id, user_id, "quiz", False, str(retry_exc), 0, 0, 0
            )
            raise AIGenerationError(
                f"Quiz generation failed twice. Last error: {retry_exc}"
            ) from retry_exc

    # Insert questions
    questions = []
    for idx, q_data in enumerate(data["questions"]):
        q = TopicQuizQuestion(
            note_id=note_id,
            position=idx + 1,
            kind=q_data["kind"],
            question=q_data["question"],
            options=q_data.get("options"),
            correct_answer=str(q_data["correct_answer"]),
            answer_explanation=q_data["answer_explanation"],
        )
        session.add(q)
        questions.append(q)

    session.commit()
    return questions


def grade_quiz_submission(
    session: Session, note_id: int, user_id: int, answers: List[Dict[str, str]]
) -> Tuple[UserQuizAttempt, List[Dict[str, Any]]]:
    """Grade submission server-side.

    Accepts answers: [{"question_id": int, "answer": str}]
    Returns (attempt_record, per_question_results)
    """
    # Load all questions
    db_questions = session.exec(
        select(TopicQuizQuestion).where(TopicQuizQuestion.note_id == note_id)
    ).all()
    q_map = {q.id: q for q in db_questions}

    results = []
    score = 0
    total = len(db_questions)

    # First pass: keep the submission order, exact-match where we can, and collect
    # every free-form (short_answer/dry_run) answer so they can be graded in ONE
    # batched Gemini call instead of one call per question.
    parsed: List[Tuple[int, TopicQuizQuestion, str]] = []
    free_form_items: List[Dict[str, Any]] = []
    for ans_dict in answers:
        q_id = int(ans_dict.get("question_id", 0))
        user_ans = ans_dict.get("answer", "").strip()
        if q_id not in q_map:
            continue
        q = q_map[q_id]
        parsed.append((q_id, q, user_ans))
        if q.kind not in ("mcq", "complexity"):
            free_form_items.append(
                {
                    "id": q_id,
                    "question": q.question,
                    "correct_answer": q.correct_answer,
                    "user_answer": user_ans,
                }
            )

    ai_grades = _grade_free_form_batch(free_form_items)

    for q_id, q, user_ans in parsed:
        if q.kind in ("mcq", "complexity"):
            correct = user_ans.lower() == q.correct_answer.lower()
        else:
            correct = ai_grades.get(q_id, user_ans.lower() == q.correct_answer.lower())

        if correct:
            score += 1

        results.append(
            {
                "question_id": q_id,
                "correct": correct,
                "your_answer": user_ans,
                "expected": q.correct_answer if not correct else None,
                "explanation": q.answer_explanation,
            }
        )

    # Save attempt
    attempt = UserQuizAttempt(
        user_id=user_id, note_id=note_id, answers=results, score=score, total=total
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)

    return attempt, results


def _grade_free_form_batch(items: List[Dict[str, Any]]) -> Dict[int, bool]:
    """Grade all free-form answers in a SINGLE Gemini call.

    ``items``: ``[{"id", "question", "correct_answer", "user_answer"}]``.
    Returns ``{question_id: is_correct}``. Falls back to case-insensitive exact
    match for everything if AI is unavailable or the call/parse fails, and for
    any individual item the model omits — so grading never hard-fails.
    """

    def _exact(it: Dict[str, Any]) -> bool:
        return it["user_answer"].strip().lower() == it["correct_answer"].strip().lower()

    if not items:
        return {}
    if not ai_available():
        return {it["id"]: _exact(it) for it in items}

    payload = [
        {
            "id": it["id"],
            "question": it["question"],
            "correct_answer": it["correct_answer"],
            "student_answer": it["user_answer"],
        }
        for it in items
    ]
    prompt = (
        "You are an automated grading system. Grade EACH student answer against its "
        "correct model answer. Be lenient on wording, syntax, spacing, and "
        "capitalization — judge conceptual correctness only.\n\n"
        f"Items (JSON array): {json.dumps(payload)}\n\n"
        'Return JSON: {"grades": [{"id": <id>, "correct": true|false}, ...]} with '
        "exactly one entry per item."
    )

    try:
        data, _, _, _ = _call_gemini_with_usage(prompt, temperature=0.1)
        grades: Dict[int, bool] = {}
        for g in data.get("grades", []):
            try:
                grades[int(g["id"])] = bool(g.get("correct", False))
            except (KeyError, TypeError, ValueError):
                continue
        # Any item the model skipped falls back to exact match.
        for it in items:
            grades.setdefault(it["id"], _exact(it))
        return grades
    except Exception:
        return {it["id"]: _exact(it) for it in items}
