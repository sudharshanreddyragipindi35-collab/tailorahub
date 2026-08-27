"""add server-side inactivity timestamp to refresh sessions

Revision ID: 20260826_0005
Revises: 20260826_0004
"""

from alembic import op
import sqlalchemy as sa

revision = "20260826_0005"
down_revision = "20260826_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("refresh_sessions", "last_activity_at")
