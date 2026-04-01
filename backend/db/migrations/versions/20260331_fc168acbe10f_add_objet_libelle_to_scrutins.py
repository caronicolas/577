"""add objet_libelle to scrutins

Revision ID: fc168acbe10f
Revises: f23d19b48a06
Create Date: 2026-03-31 20:48:49.780500+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fc168acbe10f"
down_revision: Union[str, None] = "f23d19b48a06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scrutins", sa.Column("objet_libelle", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scrutins", "objet_libelle")
