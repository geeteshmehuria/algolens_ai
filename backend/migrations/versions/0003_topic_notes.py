"""AI Topic Notes module.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create topic_notes table
    op.create_table(
        "topic_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("dsa_topics.id"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="draft"
        ),
        sa.Column(
            "level",
            sa.String(length=30),
            nullable=False,
            server_default="beginner_to_intermediate",
        ),
        sa.Column("estimated_reading_minutes", sa.Integer(), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="ai"),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("reviewed_on", sa.DateTime(), nullable=True),
        sa.Column("published_on", sa.DateTime(), nullable=True),
        sa.Column(
            "created_on", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_on", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("topic_id", "version", name="uq_topic_notes_topic_version"),
        sa.CheckConstraint(
            "status IN ('draft', 'in_review', 'published', 'archived')",
            name="chk_topic_notes_status",
        ),
        sa.CheckConstraint(
            "source IN ('ai', 'ai_edited', 'human')", name="chk_topic_notes_source"
        ),
    )

    # Partial unique index for exactly one published note per topic.
    op.create_index(
        "uq_topic_notes_one_published",
        "topic_notes",
        ["topic_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )
    op.create_index(op.f("ix_topic_notes_topic_id"), "topic_notes", ["topic_id"])

    # 2. Create topic_quiz_questions table
    op.create_table(
        "topic_quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey("topic_notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("answer_explanation", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "note_id", "position", name="uq_quiz_questions_note_position"
        ),
        sa.CheckConstraint(
            "kind IN ('mcq', 'short_answer', 'dry_run', 'complexity')",
            name="chk_quiz_questions_kind",
        ),
    )

    # 3. Create user_quiz_attempts table
    op.create_table(
        "user_quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "note_id", sa.Integer(), sa.ForeignKey("topic_notes.id"), nullable=False
        ),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column(
            "created_on", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_quiz_attempts_user", "user_quiz_attempts", ["user_id", "note_id"]
    )

    # 4. Create user_topic_note_state table
    op.create_table(
        "user_topic_note_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("dsa_topics.id"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="reading"
        ),
        sa.Column("completed_sections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("checklist_state", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "is_bookmarked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("personal_notes_md", sa.Text(), nullable=True),
        sa.Column("last_read_on", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_topic_note_state"),
        sa.CheckConstraint(
            "status IN ('reading', 'completed', 'revised')",
            name="chk_user_note_state_status",
        ),
    )
    op.create_index(
        op.f("ix_user_topic_note_state_user_id"), "user_topic_note_state", ["user_id"]
    )

    # 5. Create ai_note_generation_log table
    op.create_table(
        "ai_note_generation_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("dsa_topics.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_on", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_note_gen_log_topic", "ai_note_generation_log", ["topic_id", "created_on"]
    )

    # Seed the data for Binary Search notes, quiz, and state
    # We do a SELECT based check first to make sure Binary Search topic exists
    connection = op.get_bind()
    binary_search_topic = connection.execute(
        sa.text("SELECT id FROM dsa_topics WHERE name = 'Binary Search'")
    ).fetchone()

    if binary_search_topic:
        topic_id = binary_search_topic[0]

        # Insert draft/published note
        note_content = {
            "sections": [
                {
                    "section_key": "overview",
                    "title": "Overview",
                    "content_md": "Binary search finds a value (or boundary) in a **sorted** search space by halving it each step...",
                    "examples": [
                        "Find 9 in [-1,0,3,5,9,12]: check middle (3), too small, search right half..."
                    ],
                    "common_mistakes": [
                        "Using it on unsorted data",
                        "Infinite loop from `low = mid` instead of `low = mid + 1`",
                    ],
                    "interview_tips": [
                        "Say the magic phrase: the array is sorted, so I can binary search in O(log n)."
                    ],
                },
                {
                    "section_key": "interview_patterns",
                    "title": "Interview Patterns",
                    "content_md": "Three families: exact match, boundary search (first/last true), and binary search on the ANSWER...",
                    "examples": [],
                    "common_mistakes": [
                        "Not recognizing search-on-answer problems (Koko eating bananas style)"
                    ],
                    "interview_tips": [
                        "Keyword clues: sorted, rotated, minimum capacity, smallest x such that..."
                    ],
                },
            ],
            "pseudocode_templates": [
                {
                    "name": "Classic binary search",
                    "when_to_use": "Exact match in sorted array",
                    "pseudocode": "low = 0, high = n-1\nwhile low <= high:\n  mid = (low+high)//2\n  if a[mid]==target: return mid\n  if a[mid]<target: low = mid+1\n  else: high = mid-1\nreturn -1",
                }
            ],
            "code_templates": [
                {
                    "language": "python",
                    "name": "Classic binary search",
                    "code": "def search(nums, target):\n    low, high = 0, len(nums)-1\n    while low <= high:\n        mid = (low + high) // 2\n        if nums[mid] == target: return mid\n        if nums[mid] < target: low = mid + 1\n        else: high = mid - 1\n    return -1",
                    "line_explanations": [
                        {
                            "lines": "4",
                            "explanation": "Midpoint; Python ints do not overflow, in Java use low + (high-low)/2",
                        }
                    ],
                }
            ],
            "complexity_notes": {
                "table": [
                    {
                        "operation": "Search",
                        "time": "O(log n)",
                        "space": "O(1)",
                        "note": "Halves the space each step",
                    }
                ],
                "how_to_derive": "n -> n/2 -> n/4 ... reaches 1 after log2(n) steps.",
                "common_mistakes": [
                    "Calling recursion depth O(1) space — recursive version is O(log n) stack"
                ],
            },
            "practice_plan": {
                "one_day": [
                    "Re-read revision notes",
                    "Re-solve 1 classic + 1 boundary problem",
                    "Dry-run the template on paper",
                ],
                "seven_day": [
                    {
                        "day": 1,
                        "focus": "Classic template",
                        "tasks": ["Memorize invariant"],
                        "problems": [
                            {
                                "title": "Binary Search",
                                "difficulty": "Easy",
                                "pattern": "Classic",
                                "what_to_learn": "The loop invariant",
                                "leetcode_slug": "binary-search",
                            }
                        ],
                    }
                ],
            },
            "confidence_checklist": [
                {
                    "key": "explain_without_looking",
                    "label": "I can explain binary search without looking at notes",
                },
                {
                    "key": "boundary_variant",
                    "label": "I can write the first-true boundary variant from scratch",
                },
                {
                    "key": "complexity",
                    "label": "I can derive O(log n) instead of just stating it",
                },
            ],
        }

        import json

        note_json_str = json.dumps(note_content)

        # Insert topic_notes
        note_id = connection.execute(
            sa.text(
                "INSERT INTO topic_notes (topic_id, version, status, level, estimated_reading_minutes, content, source, model, published_on) "
                "VALUES (:topic_id, 1, 'published', 'beginner_to_intermediate', 18, :content, 'ai', 'gemini-2.5-flash', now()) "
                "RETURNING id"
            ),
            {"topic_id": topic_id, "content": note_json_str},
        ).scalar()

        # Insert topic_quiz_questions
        connection.execute(
            sa.text(
                "INSERT INTO topic_quiz_questions (note_id, position, kind, question, options, correct_answer, answer_explanation) "
                "VALUES (:note_id, 1, 'mcq', 'What is the time complexity of binary search on n sorted elements?', "
                '        \'["O(n)", "O(log n)", "O(n log n)", "O(1)"]\', \'1\', '
                "        'The search space halves each iteration: n -> n/2 -> ... -> 1 takes log2(n) steps.')"
            ),
            {"note_id": note_id},
        )

        # Find first user to seed their state
        user = connection.execute(sa.text("SELECT id FROM users LIMIT 1")).fetchone()
        if user:
            user_id = user[0]
            connection.execute(
                sa.text(
                    "INSERT INTO user_topic_note_state (user_id, topic_id, status, completed_sections, is_bookmarked) "
                    "VALUES (:user_id, :topic_id, 'reading', '[\"overview\"]', true)"
                ),
                {"user_id": user_id, "topic_id": topic_id},
            )


def downgrade() -> None:
    op.drop_table("ai_note_generation_log")
    op.drop_index(
        op.f("ix_user_topic_note_state_user_id"), table_name="user_topic_note_state"
    )
    op.drop_table("user_topic_note_state")
    op.drop_index("ix_quiz_attempts_user", table_name="user_quiz_attempts")
    op.drop_table("user_quiz_attempts")
    op.drop_table("topic_quiz_questions")
    op.drop_index(op.f("ix_topic_notes_topic_id"), table_name="topic_notes")
    op.drop_index("uq_topic_notes_one_published", table_name="topic_notes")
    op.drop_table("topic_notes")
