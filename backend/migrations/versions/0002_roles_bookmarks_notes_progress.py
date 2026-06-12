"""Roles, bookmarks, notes, per-problem progress.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=30), nullable=False, unique=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
    )
    op.create_table(
        "user_bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "problem_id", sa.Integer(), sa.ForeignKey("dsa_problems.id"), nullable=False
        ),
        sa.Column("created_on", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "problem_id", name="uq_bookmark_user_problem"),
    )
    op.create_index(op.f("ix_user_bookmarks_user_id"), "user_bookmarks", ["user_id"])
    op.create_table(
        "user_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "problem_id", sa.Integer(), sa.ForeignKey("dsa_problems.id"), nullable=False
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_on", sa.DateTime(), nullable=False),
        sa.Column("updated_on", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "problem_id", name="uq_note_user_problem"),
    )
    op.create_index(op.f("ix_user_notes_user_id"), "user_notes", ["user_id"])
    op.create_table(
        "user_problem_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "problem_id", sa.Integer(), sa.ForeignKey("dsa_problems.id"), nullable=False
        ),
        sa.Column("confidence", sa.SmallInteger(), nullable=True),
        sa.Column("updated_on", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "problem_id", name="uq_progress_user_problem"),
    )
    op.create_index(
        op.f("ix_user_problem_progress_user_id"), "user_problem_progress", ["user_id"]
    )

    # Seed the two base roles.
    roles = sa.table("roles", sa.column("name", sa.String))
    op.bulk_insert(roles, [{"name": "user"}, {"name": "admin"}])


def downgrade() -> None:
    op.drop_table("user_problem_progress")
    op.drop_table("user_notes")
    op.drop_table("user_bookmarks")
    op.drop_table("user_roles")
    op.drop_table("roles")
