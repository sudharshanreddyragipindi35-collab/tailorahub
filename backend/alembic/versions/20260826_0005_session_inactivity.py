"""add server-side inactivity timestamp to refresh sessions

Revision ID: 20260826_0005
Revises: 20260826_0004
"""

from alembic import op

revision = "20260826_0005"
down_revision = "20260826_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some early environments received this field through schema.sql before
    # Alembic was introduced. Keep the historical migration safe to rerun.
    op.execute(
        "ALTER TABLE refresh_sessions ADD COLUMN IF NOT EXISTS last_activity_at "
        "TIMESTAMPTZ NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE refresh_sessions DROP COLUMN IF EXISTS last_activity_at")
