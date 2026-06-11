"""Baseline — existing schema.

All tables up to this point (users, dsa_topics, dsa_patterns, dsa_problems,
problem_solutions, problem_animation_steps, problem_attempts, ai_code_reviews,
ai_hints, ai_generated_content, revision_queue, learning_roadmaps,
leetcode_profile_sync) were created via SQLModel.metadata.create_all before
Alembic was introduced. This revision is a no-op marker; fresh databases are
bootstrapped by init_db.py (create_all + stamp head) and every schema change
AFTER this point must ship as a real Alembic migration.

Revision ID: 0001
Revises:
Create Date: 2026-06-12

"""

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
