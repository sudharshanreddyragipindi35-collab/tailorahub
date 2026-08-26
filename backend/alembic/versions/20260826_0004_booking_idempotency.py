from alembic import op


revision = "20260826_0004"
down_revision = "20260826_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_request_id TEXT")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_customer_client_request "
        "ON orders(customer_id, client_request_id) WHERE client_request_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_orders_customer_client_request")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS client_request_id")
