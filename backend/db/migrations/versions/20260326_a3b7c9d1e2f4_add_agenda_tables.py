"""add agenda tables (seances, points_odj, reunions_commission, presences_commission)

Revision ID: a3b7c9d1e2f4
Revises: 1c2dc6336af1
Create Date: 2026-03-26 23:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3b7c9d1e2f4"
down_revision: Union[str, None] = "1c2dc6336af1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seances",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("titre", sa.Text(), nullable=True),
        sa.Column("type_seance", sa.String(50), nullable=True),
        sa.Column("is_senat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("legislature", sa.Integer(), nullable=False, server_default="17"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_seances_date", "seances", ["date"])

    op.create_table(
        "points_odj",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "seance_id",
            sa.String(100),
            sa.ForeignKey("seances.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordre", sa.Integer(), nullable=True),
        sa.Column("titre", sa.Text(), nullable=True),
    )
    op.create_index("ix_points_odj_seance_id", "points_odj", ["seance_id"])

    op.create_table(
        "reunions_commission",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("heure_debut", sa.String(10), nullable=True),
        sa.Column("heure_fin", sa.String(10), nullable=True),
        sa.Column("titre", sa.Text(), nullable=True),
        sa.Column(
            "organe_id",
            sa.String(50),
            sa.ForeignKey("organes.id"),
            nullable=True,
        ),
        sa.Column("organe_libelle", sa.String(300), nullable=True),
        sa.Column("is_senat", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("legislature", sa.Integer(), nullable=False, server_default="17"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_reunions_commission_date", "reunions_commission", ["date"])

    op.create_table(
        "presences_commission",
        sa.Column(
            "reunion_id",
            sa.String(100),
            sa.ForeignKey("reunions_commission.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "depute_id",
            sa.String(50),
            sa.ForeignKey("deputes.id"),
            primary_key=True,
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "ix_presences_commission_depute_id", "presences_commission", ["depute_id"]
    )

    op.add_column(
        "scrutins",
        sa.Column(
            "seance_id",
            sa.String(100),
            sa.ForeignKey("seances.id"),
            nullable=True,
            index=True,
        ),
    )
    op.create_index("ix_scrutins_seance_id", "scrutins", ["seance_id"])


def downgrade() -> None:
    op.drop_index("ix_scrutins_seance_id", table_name="scrutins")
    op.drop_column("scrutins", "seance_id")
    op.drop_table("presences_commission")
    op.drop_table("reunions_commission")
    op.drop_table("points_odj")
    op.drop_table("seances")
