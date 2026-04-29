"""mark old reunions_commission as already posted on bluesky

Marque toutes les réunions existantes comme déjà postées pour éviter
que le bot ne reposte l'historique au prochain CRON.
Seules les réunions ingérées après cette migration seront postées.

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-04-29 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE reunions_commission
        SET bluesky_posted_at = NOW()
        WHERE bluesky_posted_at IS NULL
        """
    )


def downgrade() -> None:
    pass
