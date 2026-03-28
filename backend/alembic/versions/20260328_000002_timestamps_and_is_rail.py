"""Convert timestamp columns from String to DateTime(timezone=True), add is_rail flag.

Revision ID: 20260328_000002
Revises: 20260325_000001
Create Date: 2026-03-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260328_000002"
down_revision: Union[str, Sequence[str], None] = "20260325_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert string timestamps to proper TIMESTAMPTZ
    # Postgres: cast in-place via ALTER COLUMN ... USING
    op.alter_column(
        "departures", "scheduled",
        type_=sa.DateTime(timezone=True),
        postgresql_using="scheduled::timestamptz",
    )
    op.alter_column(
        "departures", "estimated",
        type_=sa.DateTime(timezone=True),
        postgresql_using="NULLIF(estimated, '')::timestamptz",
    )
    op.alter_column(
        "departures", "fetched_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="fetched_at::timestamptz",
    )

    # Add is_rail boolean flag
    op.add_column(
        "departures",
        sa.Column("is_rail", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("departures", "is_rail")
    op.alter_column("departures", "scheduled", type_=sa.String())
    op.alter_column("departures", "estimated", type_=sa.String())
    op.alter_column("departures", "fetched_at", type_=sa.String())
