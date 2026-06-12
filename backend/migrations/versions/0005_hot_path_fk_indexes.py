"""Indexes for hot-path foreign keys.

problem_attempts drives live dashboard stats (streak, proficiency,
recommendations) and is always filtered by user_id/problem_id; the problems
list filters by topic_id/pattern_id; revision and hints are per-user lookups.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_problem_attempts_user_id", "problem_attempts", ["user_id"]),
    ("ix_problem_attempts_problem_id", "problem_attempts", ["problem_id"]),
    ("ix_dsa_problems_topic_id", "dsa_problems", ["topic_id"]),
    ("ix_dsa_problems_pattern_id", "dsa_problems", ["pattern_id"]),
    ("ix_revision_queue_user_id", "revision_queue", ["user_id"]),
    ("ix_revision_queue_problem_id", "revision_queue", ["problem_id"]),
    ("ix_ai_hints_user_id", "ai_hints", ["user_id"]),
    ("ix_ai_hints_problem_id", "ai_hints", ["problem_id"]),
]


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _cols in reversed(INDEXES):
        op.drop_index(name, table_name=table)
