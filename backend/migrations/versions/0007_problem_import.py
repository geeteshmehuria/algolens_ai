"""Problem import pipeline: provenance columns + import-run log.

Adds source/provenance/review-gate columns to ``dsa_problems`` (all nullable or
server-defaulted, so existing rows and their FKs are untouched) and a partial
unique index that makes re-imports idempotent. Creates the ``problem_import_runs``
audit table. Existing problems inherit ``source_type='seed'`` /
``import_status='published'`` from the column server defaults, so nothing that is
currently visible disappears.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-16

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dsa_problems",
        sa.Column(
            "source_type",
            sa.String(length=20),
            nullable=False,
            server_default="seed",
        ),
    )
    op.add_column(
        "dsa_problems", sa.Column("source_name", sa.String(length=60), nullable=True)
    )
    op.add_column(
        "dsa_problems", sa.Column("external_id", sa.String(length=120), nullable=True)
    )
    op.add_column("dsa_problems", sa.Column("external_url", sa.Text(), nullable=True))
    op.add_column(
        "dsa_problems", sa.Column("title_slug", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "dsa_problems",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "dsa_problems",
        sa.Column(
            "import_status",
            sa.String(length=20),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "dsa_problems",
        sa.Column(
            "is_premium",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "dsa_problems", sa.Column("attribution", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "dsa_problems",
        sa.Column("interview_frequency_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "dsa_problems",
        sa.Column("learning_priority_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "dsa_problems",
        sa.Column(
            "updated_on",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Backfill the dedup key for existing rows from their slug.
    op.execute(
        "UPDATE dsa_problems SET title_slug = lower(regexp_replace(title, '[^a-zA-Z0-9]+', '-', 'g')) "
        "WHERE title_slug IS NULL"
    )

    op.create_index(op.f("ix_dsa_problems_title_slug"), "dsa_problems", ["title_slug"])
    op.create_index(
        op.f("ix_dsa_problems_import_status"), "dsa_problems", ["import_status"]
    )
    # Idempotency: one row per (source_name, leetcode_slug) when both present.
    op.create_index(
        "uq_problem_source_slug",
        "dsa_problems",
        ["source_name", "leetcode_slug"],
        unique=True,
        postgresql_where=sa.text(
            "source_name IS NOT NULL AND leetcode_slug IS NOT NULL"
        ),
    )

    op.create_table(
        "problem_import_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="running"
        ),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "skipped_duplicate_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("problem_import_runs")
    op.drop_index("uq_problem_source_slug", table_name="dsa_problems")
    op.drop_index(op.f("ix_dsa_problems_import_status"), table_name="dsa_problems")
    op.drop_index(op.f("ix_dsa_problems_title_slug"), table_name="dsa_problems")
    for col in (
        "updated_on",
        "learning_priority_score",
        "interview_frequency_score",
        "attribution",
        "is_premium",
        "import_status",
        "tags",
        "title_slug",
        "external_url",
        "external_id",
        "source_name",
        "source_type",
    ):
        op.drop_column("dsa_problems", col)
