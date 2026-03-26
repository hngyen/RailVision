"""add is_rail boolean flag to replace regex filtering

Revision ID: 20260326_000003
Revises: 20260326_000002
Create Date: 2026-03-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260326_000003"
down_revision: Union[str, Sequence[str], None] = "20260326_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "departures",
        sa.Column("is_rail", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Backfill existing rows where line matches rail pattern (T1, L2, M1, S1, etc.)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("UPDATE departures SET is_rail = true WHERE line ~ '^[TLMS][0-9]$'")
    else:
        # SQLite GLOB supports character classes
        op.execute("UPDATE departures SET is_rail = 1 WHERE line GLOB '[TLMS][0-9]'")


def downgrade() -> None:
    op.drop_column("departures", "is_rail")
