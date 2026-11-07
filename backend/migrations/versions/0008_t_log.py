"""Failure log table ``t_log``.

Every failed API request (status >= 400) and unhandled exception is recorded
with the real underlying cause (e.g. the Gemini quota/overload message), so
"AI response could not be generated" can be diagnosed from SQL instead of
server stdout. Successful requests are not logged.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-07

"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=200), nullable=False),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("origin", sa.String(length=200), nullable=True),
        sa.Column("user_agent", sa.String(length=200), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_t_log_created_at", "t_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_t_log_created_at", table_name="t_log")
    op.drop_table("t_log")
