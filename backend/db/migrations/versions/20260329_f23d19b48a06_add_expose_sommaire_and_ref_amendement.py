"""add_expose_sommaire_and_ref_amendement

Revision ID: f23d19b48a06
Revises: a3b7c9d1e2f4
Create Date: 2026-03-29 18:55:26.498437+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f23d19b48a06"
down_revision: Union[str, None] = "a3b7c9d1e2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("amendements", sa.Column("expose_sommaire", sa.Text(), nullable=True))
    op.add_column(
        "scrutins", sa.Column("ref_amendement", sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scrutins", "ref_amendement")
    op.drop_column("amendements", "expose_sommaire")
