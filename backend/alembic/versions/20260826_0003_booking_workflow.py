from __future__ import annotations

from pathlib import Path

from alembic import op
from app.utils.sql_script import execute_postgresql_script


revision = "20260826_0003"
down_revision = "20260809_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "app" / "schema.sql"
    execute_postgresql_script(op, schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    # This migration is additive and preserves production booking data.
    pass
