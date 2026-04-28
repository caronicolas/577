"""mark old scrutins as already posted on bluesky

Marque tous les scrutins solennels et motions de censure antérieurs
à aujourd'hui comme déjà postés, pour éviter que le bot ne reposte
l'historique complet de la législature.

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
Create Date: 2026-04-28 00:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TYPES_A_POSTER = ("scrutin public solennel", "motion de censure")


def upgrade() -> None:
    op.execute(
        """
        UPDATE scrutins
        SET bluesky_posted_at = NOW()
        WHERE bluesky_posted_at IS NULL
          AND type_vote = ANY(ARRAY['scrutin public solennel', 'motion de censure'])
          AND date_seance < CURRENT_DATE - INTERVAL '3 days'
        """
    )


def downgrade() -> None:
    pass
