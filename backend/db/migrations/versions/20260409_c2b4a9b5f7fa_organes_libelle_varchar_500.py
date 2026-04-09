"""organes libelle varchar 500

Revision ID: c2b4a9b5f7fa
Revises: b3c4d5e6f7a8
Create Date: 2026-04-09 20:03:26.884851+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2b4a9b5f7fa"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "organes",
        "libelle",
        existing_type=sa.VARCHAR(length=200),
        type_=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "organes",
        "libelle",
        existing_type=sa.String(length=500),
        type_=sa.VARCHAR(length=200),
        existing_nullable=False,
    )
