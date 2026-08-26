from __future__ import annotations

from pathlib import Path

from alembic import op
from app.utils.sql_script import execute_postgresql_script


revision = "20260809_0002"
down_revision = "20260809_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # schema.sql is written to be safely re-runnable (CREATE ... IF NOT
    # EXISTS / ADD COLUMN IF NOT EXISTS / guarded DO blocks throughout),
    # so re-executing the whole file picks up the reconciliation DDL
    # appended after revision 0001 without disturbing anything already
    # applied. Same approach as 0001.
    schema_path = Path(__file__).resolve().parents[2] / "app" / "schema.sql"
    execute_postgresql_script(op, schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Additive/reconciliation migration for an existing app. Do not drop
    # production tables automatically.
    pass
