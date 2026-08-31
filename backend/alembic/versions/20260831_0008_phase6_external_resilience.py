"""add phase 6 payment idempotency and webhook receipt ledger

Revision ID: 20260831_0008
Revises: 20260830_0007
"""

from alembic import op


revision = "20260831_0008"
down_revision = "20260830_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE payment_intents ADD COLUMN IF NOT EXISTS client_request_id TEXT")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_intents_customer_request "
        "ON payment_intents(customer_id, client_request_id) WHERE client_request_id IS NOT NULL"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_webhook_events (
          provider TEXT NOT NULL,
          event_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          payload_sha256 TEXT NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('processing','completed','ignored','failed')),
          gateway_order_id TEXT,
          gateway_payment_id TEXT,
          booking_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
          last_error TEXT,
          received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          processed_at TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (provider, event_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS payment_webhook_status_updated_idx "
        "ON payment_webhook_events(status, updated_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS payment_webhook_status_updated_idx")
    op.execute("DROP TABLE IF EXISTS payment_webhook_events")
    op.execute("DROP INDEX IF EXISTS uq_payment_intents_customer_request")
    op.execute("ALTER TABLE payment_intents DROP COLUMN IF EXISTS client_request_id")
