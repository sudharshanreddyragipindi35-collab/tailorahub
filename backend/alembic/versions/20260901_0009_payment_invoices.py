"""add idempotent payment invoices

Revision ID: 20260901_0009
Revises: 20260831_0008
"""

from alembic import op


revision = "20260901_0009"
down_revision = "20260831_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          invoice_number TEXT UNIQUE NOT NULL,
          booking_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
          payment_intent_id UUID REFERENCES payment_intents(id) ON DELETE SET NULL,
          customer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          gateway_payment_id TEXT UNIQUE NOT NULL,
          gateway_order_id TEXT NOT NULL,
          amount NUMERIC(12,2) NOT NULL,
          currency TEXT NOT NULL DEFAULT 'INR',
          pdf_reference TEXT NOT NULL,
          email_status TEXT NOT NULL DEFAULT 'pending' CHECK (email_status IN ('pending','queued','sent','failed')),
          email_error TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          emailed_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS invoices_payment_intent_idx ON invoices(payment_intent_id) WHERE payment_intent_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS invoices_customer_created_idx ON invoices(customer_id,created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS invoices_customer_created_idx")
    op.execute("DROP INDEX IF EXISTS invoices_payment_intent_idx")
    op.execute("DROP TABLE IF EXISTS invoices")
