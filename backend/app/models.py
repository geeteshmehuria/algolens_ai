# app/models.py
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint


# --- USER MODULE ---
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = Field(default=None, max_length=150)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str
    leetcode_username: Optional[str] = Field(default=None, max_length=100)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    attempts: List["ProblemAttempt"] = Relationship(back_populates="user")
    hints: List["AIHint"] = Relationship(back_populates="user")
    revisions: List["RevisionQueue"] = Relationship(back_populates="user")
    roadmaps: List["LearningRoadmap"] = Relationship(back_populates="user")
    leetcode_syncs: List["LeetCodeProfileSync"] = Relationship(back_populates="user")


# --- ROLES ---
class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=30)  # 'user', 'admin'


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)


# --- TOPIC & PATTERN MODULES ---
class DSATopic(SQLModel, table=True):
    __tablename__ = "dsa_topics"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    patterns: List["DSAPattern"] = Relationship(back_populates="topic")
    problems: List["DSAProblem"] = Relationship(back_populates="topic")


class DSAPattern(SQLModel, table=True):
    __tablename__ = "dsa_patterns"

    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="dsa_topics.id")
    name: str = Field(max_length=150)
    description: Optional[str] = Field(default=None)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    topic: DSATopic = Relationship(back_populates="patterns")
    problems: List["DSAProblem"] = Relationship(back_populates="pattern")


# --- PROBLEM MODULES ---
class DSAProblem(SQLModel, table=True):
    __tablename__ = "dsa_problems"

    id: Optional[int] = Field(default=None, primary_key=True)
    leetcode_slug: Optional[str] = Field(default=None, max_length=255)
    leetcode_url: Optional[str] = Field(default=None)
    title: str = Field(max_length=255)
    difficulty: str = Field(max_length=20)  # Easy, Medium, Hard
    topic_id: int = Field(foreign_key="dsa_topics.id")
    pattern_id: int = Field(foreign_key="dsa_patterns.id")
    description: str
    constraints_text: Optional[str] = Field(default=None)
    examples: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    starter_code: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    topic: DSATopic = Relationship(back_populates="problems")
    pattern: DSAPattern = Relationship(back_populates="problems")
    solutions: List["ProblemSolution"] = Relationship(back_populates="problem")
    animation_steps: List["ProblemAnimationStep"] = Relationship(
        back_populates="problem"
    )
    attempts: List["ProblemAttempt"] = Relationship(back_populates="problem")
    hints: List["AIHint"] = Relationship(back_populates="problem")
    revisions: List["RevisionQueue"] = Relationship(back_populates="problem")


class ProblemSolution(SQLModel, table=True):
    __tablename__ = "problem_solutions"

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="dsa_problems.id")
    approach_type: str = Field(max_length=50)  # e.g., 'Brute Force', 'Optimized'
    explanation: str
    pseudocode: List[str] = Field(default=[], sa_column=Column(JSON))
    time_complexity: str = Field(max_length=50)
    space_complexity: str = Field(max_length=50)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    problem: DSAProblem = Relationship(back_populates="solutions")


class ProblemAnimationStep(SQLModel, table=True):
    __tablename__ = "problem_animation_steps"

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="dsa_problems.id")
    animation_type: str = Field(max_length=100)  # e.g., 'hash_map_array', 'stack'
    step_order: int
    step_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    explanation: Optional[str] = Field(default=None)
    pseudocode_line: Optional[int] = Field(default=None)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    problem: DSAProblem = Relationship(back_populates="animation_steps")


# --- ATTEMPT MODULES ---
class ProblemAttempt(SQLModel, table=True):
    __tablename__ = "problem_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    problem_id: int = Field(foreign_key="dsa_problems.id")
    submitted_code: str
    status: str = Field(max_length=30)  # e.g., 'Correct', 'Incorrect', 'Reviewing'
    used_hint: bool = Field(default=False)
    ai_score: Optional[float] = Field(default=None)
    time_complexity: Optional[str] = Field(default=None, max_length=50)
    space_complexity: Optional[str] = Field(default=None, max_length=50)
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="attempts")
    problem: DSAProblem = Relationship(back_populates="attempts")
    reviews: List["AICodeReview"] = Relationship(back_populates="attempt")


class AICodeReview(SQLModel, table=True):
    __tablename__ = "ai_code_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(foreign_key="problem_attempts.id")
    is_correct: bool
    logic_feedback: str
    bugs: List[str] = Field(default=[], sa_column=Column(JSON))
    missed_edge_cases: List[str] = Field(default=[], sa_column=Column(JSON))
    better_approach: Optional[str] = Field(default=None)
    dsa_pattern: Optional[str] = Field(default=None, max_length=150)
    time_complexity: Optional[str] = Field(default=None, max_length=50)
    space_complexity: Optional[str] = Field(default=None, max_length=50)
    score: float
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    attempt: ProblemAttempt = Relationship(back_populates="reviews")


class AIGeneratedContent(SQLModel, table=True):
    """Shared cache of AI-generated content per problem.

    One row per (problem, kind) — e.g. kind='explanation' or kind='animation'.
    Generated once via Gemini, then served to every user from the database
    so repeat requests cost zero AI tokens.
    """

    __tablename__ = "ai_generated_content"
    __table_args__ = (
        UniqueConstraint("problem_id", "kind", name="uq_ai_content_problem_kind"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="dsa_problems.id", index=True)
    kind: str = Field(max_length=30)  # 'explanation' | 'animation'
    content: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    model: str = Field(default="", max_length=80)
    created_on: datetime = Field(default_factory=datetime.utcnow)


class AIHint(SQLModel, table=True):
    __tablename__ = "ai_hints"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    problem_id: int = Field(foreign_key="dsa_problems.id")
    hint_level: int
    hint_text: str
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="hints")
    problem: DSAProblem = Relationship(back_populates="hints")


# --- USER LEARNING STATE ---
class UserBookmark(SQLModel, table=True):
    __tablename__ = "user_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_bookmark_user_problem"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    problem_id: int = Field(foreign_key="dsa_problems.id")
    created_on: datetime = Field(default_factory=datetime.utcnow)


class UserNote(SQLModel, table=True):
    __tablename__ = "user_notes"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_note_user_problem"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    problem_id: int = Field(foreign_key="dsa_problems.id")
    content: str
    created_on: datetime = Field(default_factory=datetime.utcnow)
    updated_on: datetime = Field(default_factory=datetime.utcnow)


class UserProblemProgress(SQLModel, table=True):
    """Per-user, per-problem learning state (currently self-rated confidence;
    a natural home for future fields like status or last_reviewed)."""

    __tablename__ = "user_problem_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_progress_user_problem"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    problem_id: int = Field(foreign_key="dsa_problems.id")
    confidence: Optional[int] = Field(
        default=None, ge=1, le=5
    )  # 1 = relearn, 5 = interview-ready
    updated_on: datetime = Field(default_factory=datetime.utcnow)


# --- REVISION QUEUE ---
class RevisionQueue(SQLModel, table=True):
    __tablename__ = "revision_queue"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    problem_id: int = Field(foreign_key="dsa_problems.id")
    due_date: date
    reason: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(
        default="pending", max_length=30
    )  # e.g., 'pending', 'completed'
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="revisions")
    problem: DSAProblem = Relationship(back_populates="revisions")


# --- ROADMAP & SYNC MODULES ---
class LearningRoadmap(SQLModel, table=True):
    __tablename__ = "learning_roadmaps"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    title: Optional[str] = Field(default=None, max_length=255)
    roadmap_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="roadmaps")


class LeetCodeProfileSync(SQLModel, table=True):
    __tablename__ = "leetcode_profile_sync"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    leetcode_username: str = Field(max_length=100)
    total_solved: int = Field(default=0)
    easy_solved: int = Field(default=0)
    medium_solved: int = Field(default=0)
    hard_solved: int = Field(default=0)
    last_synced_on: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="leetcode_syncs")


# --- TOPIC NOTES MODULE ---


class TopicNote(SQLModel, table=True):
    __tablename__ = "topic_notes"
    __table_args__ = (
        UniqueConstraint("topic_id", "version", name="uq_topic_notes_topic_version"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="dsa_topics.id", index=True)
    version: int = Field(default=1)
    status: str = Field(default="draft", max_length=20)
    level: str = Field(default="beginner_to_intermediate", max_length=30)
    estimated_reading_minutes: Optional[int] = Field(default=None)
    schema_version: int = Field(default=1)
    content: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    source: str = Field(default="ai", max_length=20)
    model: Optional[str] = Field(default=None, max_length=80)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_on: Optional[datetime] = Field(default=None)
    published_on: Optional[datetime] = Field(default=None)
    created_on: datetime = Field(default_factory=datetime.utcnow)
    updated_on: datetime = Field(default_factory=datetime.utcnow)


class TopicQuizQuestion(SQLModel, table=True):
    __tablename__ = "topic_quiz_questions"
    __table_args__ = (
        UniqueConstraint("note_id", "position", name="uq_quiz_questions_note_position"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    note_id: int = Field(foreign_key="topic_notes.id", ondelete="CASCADE")
    position: int
    kind: str = Field(max_length=20)  # 'mcq', 'short_answer', 'dry_run', 'complexity'
    question: str
    options: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    correct_answer: str
    answer_explanation: str


class UserQuizAttempt(SQLModel, table=True):
    __tablename__ = "user_quiz_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    note_id: int = Field(foreign_key="topic_notes.id")
    answers: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    score: int
    total: int
    created_on: datetime = Field(default_factory=datetime.utcnow)


class UserTopicNoteState(SQLModel, table=True):
    __tablename__ = "user_topic_note_state"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_note_state"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    topic_id: int = Field(foreign_key="dsa_topics.id")
    status: str = Field(
        default="reading", max_length=20
    )  # 'reading', 'completed', 'revised'
    completed_sections: List[str] = Field(default=[], sa_column=Column(JSON))
    checklist_state: Dict[str, bool] = Field(default={}, sa_column=Column(JSON))
    is_bookmarked: bool = Field(default=False)
    personal_notes_md: Optional[str] = Field(default=None)
    last_read_on: Optional[datetime] = Field(default=None)


class AINoteGenerationLog(SQLModel, table=True):
    __tablename__ = "ai_note_generation_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="dsa_topics.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    kind: str = Field(max_length=30)  # 'notes_learn', 'notes_apply', etc.
    model: str = Field(max_length=80)
    success: bool
    error: Optional[str] = Field(default=None)
    input_tokens: Optional[int] = Field(default=None)
    output_tokens: Optional[int] = Field(default=None)
    latency_ms: Optional[int] = Field(default=None)
    created_on: datetime = Field(default_factory=datetime.utcnow)
