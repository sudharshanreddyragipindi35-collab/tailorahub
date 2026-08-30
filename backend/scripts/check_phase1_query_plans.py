"""Read-only query-plan smoke check for Phase 1 collection endpoints.

Run from ``backend`` with ``python scripts/check_phase1_query_plans.py``.
The script never prints connection strings, parameters, or customer data.
"""

from __future__ import annotations

from sqlalchemy import text

from app.db import engine


QUERIES = {
    "customer_orders": "SELECT id FROM orders WHERE customer_id=:value ORDER BY ts DESC LIMIT 50",
    "tailor_orders": "SELECT id FROM orders WHERE tailor_id=:value ORDER BY ts DESC LIMIT 50",
    "tailor_requests": "SELECT id FROM booking_requests WHERE tailor_id=:value ORDER BY ts DESC LIMIT 50",
    "notifications": "SELECT id FROM notifications WHERE to_ref=:value ORDER BY ts DESC LIMIT 50",
    "support_tickets": "SELECT id FROM support_tickets WHERE requester_id=:value AND requester_role='customer' ORDER BY last_activity_at DESC LIMIT 50",
}


def main() -> None:
    with engine.connect() as connection:
        samples = {
            "customer_orders": connection.execute(text("SELECT customer_id FROM orders LIMIT 1")).scalar(),
            "tailor_orders": connection.execute(text("SELECT tailor_id FROM orders LIMIT 1")).scalar(),
            "tailor_requests": connection.execute(text("SELECT tailor_id FROM booking_requests LIMIT 1")).scalar(),
            "notifications": connection.execute(text("SELECT to_ref FROM notifications LIMIT 1")).scalar(),
            "support_tickets": connection.execute(text("SELECT requester_id FROM support_tickets WHERE requester_role='customer' LIMIT 1")).scalar(),
        }
        for name, query in QUERIES.items():
            value = samples[name]
            if value is None:
                print(f"{name}: skipped (no sample row)")
                continue
            plan_result = connection.execute(
                text(f"EXPLAIN (FORMAT JSON, COSTS TRUE) {query}"),
                {"value": value},
            ).scalar_one()
            plan = plan_result[0]["Plan"]
            print(
                f"{name}: node={plan['Node Type']} "
                f"estimated_rows={plan.get('Plan Rows', 0)} "
                f"total_cost={plan.get('Total Cost', 0)}"
            )


if __name__ == "__main__":
    main()
