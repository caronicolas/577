"""add datan tables

Revision ID: a1b2c3d4e5f6
Revises: eea15b80cfa1
Create Date: 2026-04-03
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "eea15b80cfa1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datan_deputes",
        sa.Column("identifiant_an", sa.Text(), nullable=False),
        sa.Column("score_participation", sa.Float(), nullable=True),
        sa.Column("score_participation_specialite", sa.Float(), nullable=True),
        sa.Column("score_loyaute", sa.Float(), nullable=True),
        sa.Column("score_majorite", sa.Float(), nullable=True),
        sa.Column("date_maj", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("identifiant_an"),
    )
    op.create_table(
        "datan_groupes",
        sa.Column("libelle_abrev", sa.Text(), nullable=False),
        sa.Column("score_cohesion", sa.Float(), nullable=True),
        sa.Column("score_participation", sa.Float(), nullable=True),
        sa.Column("score_majorite", sa.Float(), nullable=True),
        sa.Column("women_pct", sa.Float(), nullable=True),
        sa.Column("age_moyen", sa.Float(), nullable=True),
        sa.Column("score_rose", sa.Float(), nullable=True),
        sa.Column("position_politique", sa.Text(), nullable=True),
        sa.Column("date_maj", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("libelle_abrev"),
    )


def downgrade() -> None:
    op.drop_table("datan_groupes")
    op.drop_table("datan_deputes")
