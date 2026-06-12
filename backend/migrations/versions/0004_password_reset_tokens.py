"""Password reset tokens.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_on", sa.DateTime(), nullable=False),
        sa.Column("used_on", sa.DateTime(), nullable=True),
        sa.Column(
            "created_on", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"),
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires_on",
        "password_reset_tokens",
        ["expires_on"],
    )

    # Normalize any pre-existing emails so the (now-normalized) login lookup
    # always matches. Safe: users.email has a unique constraint, so this will
    # fail loudly rather than silently merge two accounts that differ only by
    # case (none exist at the time of writing).
    op.execute(
        "UPDATE users SET email = lower(trim(email)) WHERE email != lower(trim(email))"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_tokens_expires_on", table_name="password_reset_tokens"
    )
    op.drop_index(
        op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
