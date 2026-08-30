"""add phase 1 collection query indexes

Revision ID: 20260830_0006
Revises: 20260826_0005
"""

from alembic import op


revision = "20260830_0006"
down_revision = "20260826_0005"
branch_labels = None
depends_on = None


INDEXES = (
    "CREATE INDEX IF NOT EXISTS orders_customer_ts_idx ON orders(customer_id, ts DESC)",
    "CREATE INDEX IF NOT EXISTS orders_tailor_status_ts_idx ON orders(tailor_id, status, ts DESC)",
    "CREATE INDEX IF NOT EXISTS booking_requests_tailor_status_ts_idx ON booking_requests(tailor_id, status, ts DESC)",
    "CREATE INDEX IF NOT EXISTS booking_requirements_customer_ts_idx ON booking_requirements(customer_id, ts DESC)",
    "CREATE INDEX IF NOT EXISTS payments_status_ts_idx ON payments(status, ts DESC)",
    "CREATE INDEX IF NOT EXISTS reviews_tailor_hidden_ts_idx ON reviews(tailor_id, hidden, ts DESC)",
    "CREATE INDEX IF NOT EXISTS support_tickets_requester_activity_idx ON support_tickets(requester_id, requester_role, last_activity_at DESC)",
    "CREATE INDEX IF NOT EXISTS complaints_status_ts_idx ON complaints(status, ts DESC)",
)


def upgrade() -> None:
    for statement in INDEXES:
        op.execute(statement)


def downgrade() -> None:
    for name in (
        "complaints_status_ts_idx",
        "support_tickets_requester_activity_idx",
        "reviews_tailor_hidden_ts_idx",
        "payments_status_ts_idx",
        "booking_requirements_customer_ts_idx",
        "booking_requests_tailor_status_ts_idx",
        "orders_tailor_status_ts_idx",
        "orders_customer_ts_idx",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
