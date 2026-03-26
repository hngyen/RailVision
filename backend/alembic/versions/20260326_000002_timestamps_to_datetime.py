"""convert timestamp columns from string to datetime

Revision ID: 20260326_000002
Revises: 20260325_000001
Create Date: 2026-03-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260326_000002"
down_revision: Union[str, Sequence[str], None] = "20260325_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    if conn.dialect.name == "postgresql":
        # Drop unique constraint so type conversion doesn't collide on duplicates
        op.drop_constraint("unique_departure", "departures", type_="unique")

        # Deduplicate: keep only the row with the latest fetched_at per logical trip
        op.execute(
            "DELETE FROM departures d1 USING departures d2 "
            "WHERE d1.line = d2.line AND d1.scheduled = d2.scheduled "
            "AND d1.stop_id = d2.stop_id AND d1.fetched_at < d2.fetched_at"
        )

        # Now safe to convert types
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN scheduled TYPE TIMESTAMPTZ USING scheduled::timestamptz"
        )
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN estimated TYPE TIMESTAMPTZ USING NULLIF(estimated, '')::timestamptz"
        )
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN fetched_at TYPE TIMESTAMPTZ USING fetched_at::timestamptz"
        )

        # Re-add unique constraint on the now-clean data
        op.create_unique_constraint("unique_departure", "departures", ["line", "scheduled", "stop_id"])
    else:
        # SQLite: recreate table with new column types via batch
        with op.batch_alter_table("departures", schema=None) as batch_op:
            batch_op.alter_column("scheduled", type_=sa.DateTime(timezone=True))
            batch_op.alter_column("estimated", type_=sa.DateTime(timezone=True))
            batch_op.alter_column("fetched_at", type_=sa.DateTime(timezone=True))


def downgrade() -> None:
    conn = op.get_bind()

    if conn.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN scheduled TYPE VARCHAR USING scheduled::text"
        )
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN estimated TYPE VARCHAR USING estimated::text"
        )
        op.execute(
            "ALTER TABLE departures "
            "ALTER COLUMN fetched_at TYPE VARCHAR USING fetched_at::text"
        )
    else:
        with op.batch_alter_table("departures", schema=None) as batch_op:
            batch_op.alter_column("scheduled", type_=sa.String())
            batch_op.alter_column("estimated", type_=sa.String())
            batch_op.alter_column("fetched_at", type_=sa.String())
