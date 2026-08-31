"""add phase 4 background job receipt ledger

Revision ID: 20260830_0007
Revises: 20260830_0006
"""

from alembic import op


revision = "20260830_0007"
down_revision = "20260830_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS background_job_receipts (
          idempotency_key TEXT PRIMARY KEY,
          job_id TEXT NOT NULL,
          job_type TEXT NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('processing','completed','failed')),
          attempts INTEGER NOT NULL DEFAULT 0,
          result JSONB NOT NULL DEFAULT '{}'::jsonb,
          last_error TEXT,
          started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          completed_at TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS background_job_status_updated_idx ON background_job_receipts(status, updated_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS background_job_status_updated_idx")
    op.execute("DROP TABLE IF EXISTS background_job_receipts")
