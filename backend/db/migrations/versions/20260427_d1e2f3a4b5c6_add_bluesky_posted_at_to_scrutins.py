"""add bluesky_posted_at to scrutins

Revision ID: d1e2f3a4b5c6
Revises: c2b4a9b5f7fa
Create Date: 2026-04-27 10:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c2b4a9b5f7fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scrutins",
        sa.Column("bluesky_posted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scrutins", "bluesky_posted_at")
