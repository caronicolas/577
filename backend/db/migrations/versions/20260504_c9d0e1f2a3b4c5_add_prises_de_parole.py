"""add prises_de_parole table

Revision ID: c9d0e1f2a3b4c5
Revises: f5a6b7c8d9e0
Create Date: 2026-05-04 00:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4c5"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("prises_de_parole"):
        op.create_table(
            "prises_de_parole",
            sa.Column(
                "depute_id", sa.String(50), sa.ForeignKey("deputes.id"), nullable=False
            ),
            sa.Column("seance_id", sa.String(100), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("legislature", sa.Integer(), nullable=False, server_default="17"),
            sa.PrimaryKeyConstraint("depute_id", "seance_id"),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prises_de_parole_depute_id "
        "ON prises_de_parole (depute_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prises_de_parole_date ON prises_de_parole (date)"
    )


def downgrade() -> None:
    op.drop_index("ix_prises_de_parole_date", table_name="prises_de_parole")
    op.drop_index("ix_prises_de_parole_depute_id", table_name="prises_de_parole")
    op.drop_table("prises_de_parole")
