"""bootstrap migration chain

Revision ID: 20260325_000001
Revises:
Create Date: 2026-03-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departures",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("line", sa.String()),
        sa.Column("line_name", sa.String()),
        sa.Column("destination", sa.String()),
        sa.Column("operator", sa.String()),
        sa.Column("platform", sa.String()),
        sa.Column("scheduled", sa.String()),
        sa.Column("estimated", sa.String()),
        sa.Column("delay_min", sa.Float()),
        sa.Column("realtime", sa.Boolean()),
        sa.Column("stop_id", sa.String()),
        sa.Column("fetched_at", sa.String()),
        sa.UniqueConstraint("line", "scheduled", "stop_id", name="unique_departure"),
    )
    op.create_index("idx_line_scheduled", "departures", ["line", "scheduled"])
    op.create_index("idx_stop_scheduled", "departures", ["stop_id", "scheduled"])


def downgrade() -> None:
    op.drop_index("idx_stop_scheduled", table_name="departures")
    op.drop_index("idx_line_scheduled", table_name="departures")
    op.drop_table("departures")
