"""Curriculum metadata on dsa_topics.

Enriches the flat topic table so each topic can carry curriculum structure:
slug (stable idempotency key for the seed), category grouping, difficulty,
learning_order, estimated time, prerequisites/tags, and an is_active flag.
All columns are nullable / defaulted so existing rows and their problem links
are untouched; the curriculum seed backfills slugs and metadata.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dsa_topics", sa.Column("slug", sa.String(length=120), nullable=True))
    op.add_column(
        "dsa_topics", sa.Column("category", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "dsa_topics", sa.Column("difficulty", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "dsa_topics", sa.Column("learning_order", sa.Integer(), nullable=True)
    )
    op.add_column(
        "dsa_topics", sa.Column("estimated_time_minutes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "dsa_topics",
        sa.Column(
            "prerequisites",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "dsa_topics",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "dsa_topics",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "dsa_topics",
        sa.Column(
            "updated_on",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(op.f("ix_dsa_topics_slug"), "dsa_topics", ["slug"], unique=True)
    op.create_index(
        op.f("ix_dsa_topics_learning_order"), "dsa_topics", ["learning_order"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_dsa_topics_learning_order"), table_name="dsa_topics")
    op.drop_index(op.f("ix_dsa_topics_slug"), table_name="dsa_topics")
    for col in (
        "updated_on",
        "is_active",
        "tags",
        "prerequisites",
        "estimated_time_minutes",
        "learning_order",
        "difficulty",
        "category",
        "slug",
    ):
        op.drop_column("dsa_topics", col)
