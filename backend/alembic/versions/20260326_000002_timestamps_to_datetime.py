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
        # Drop constraint and indexes that reference columns we're converting
        op.execute("ALTER TABLE departures DROP CONSTRAINT IF EXISTS unique_departure")
        op.execute("DROP INDEX IF EXISTS idx_line_scheduled")
        op.execute("DROP INDEX IF EXISTS idx_stop_scheduled")

        # Deduplicate using id (handles rows with identical fetched_at)
        op.execute(
            "DELETE FROM departures d1 USING departures d2 "
            "WHERE d1.line = d2.line AND d1.scheduled = d2.scheduled "
            "AND d1.stop_id = d2.stop_id AND d1.id < d2.id"
        )

        # Now safe to convert types — no indexes to rebuild
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

        # Recreate constraint and indexes on clean, converted data
        op.create_unique_constraint("unique_departure", "departures", ["line", "scheduled", "stop_id"])
        op.create_index("idx_line_scheduled", "departures", ["line", "scheduled"])
        op.create_index("idx_stop_scheduled", "departures", ["stop_id", "scheduled"])
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
