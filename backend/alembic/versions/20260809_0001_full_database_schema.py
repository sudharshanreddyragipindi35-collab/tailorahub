from __future__ import annotations

from pathlib import Path

from alembic import op


revision = "20260809_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "app" / "schema.sql"
    op.execute(schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    # This first migration is intentionally additive for an existing app.
    # Do not drop production tables automatically.
    pass
