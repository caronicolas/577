from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import DatanGroupe, Depute, Organe
from db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class DatanGroupeSchema(BaseModel):
    score_cohesion: Optional[float]
    score_participation: Optional[float]
    score_majorite: Optional[float]
    women_pct: Optional[float]
    age_moyen: Optional[float]
    score_rose: Optional[float]
    position_politique: Optional[str]


class GroupeListItem(BaseModel):
    id: str
    sigle: str
    libelle: str
    couleur: Optional[str]
    nb_deputes: int
    datan: Optional[DatanGroupeSchema]


class DeputeInGroupe(BaseModel):
    id: str
    prenom: str
    nom_de_famille: str
    url_photo: Optional[str]
    num_departement: Optional[str]
    nom_circonscription: Optional[str]
    actif: bool


class GroupeDetail(BaseModel):
    id: str
    sigle: str
    libelle: str
    couleur: Optional[str]
    nb_deputes: int
    nb_deputes_total: int
    datan: Optional[DatanGroupeSchema]
    deputes: list[DeputeInGroupe]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[GroupeListItem])
async def list_groupes(
    session: AsyncSession = Depends(get_session),
) -> list[GroupeListItem]:
    """Liste des groupes parlementaires avec statistiques Datan."""
    stmt = (
        select(Organe, func.count(Depute.id).label("nb"))
        .join(Depute, Depute.groupe_id == Organe.id)
        .where(Depute.actif.is_(True))
        .group_by(Organe.id)
        .having(func.count(Depute.id) > 0)
        .order_by(func.count(Depute.id).desc())
    )
    rows = (await session.execute(stmt)).all()

    sigles = [row.Organe.sigle for row in rows]
    datan_rows = (
        (
            await session.execute(
                select(DatanGroupe).where(DatanGroupe.libelle_abrev.in_(sigles))
            )
        )
        .scalars()
        .all()
    )
    datan_map = {d.libelle_abrev: d for d in datan_rows}

    result = []
    for row in rows:
        organe = row.Organe
        datan = datan_map.get(organe.sigle)
        result.append(
            GroupeListItem(
                id=organe.id,
                sigle=organe.sigle,
                libelle=organe.libelle,
                couleur=organe.couleur,
                nb_deputes=row.nb,
                datan=(
                    DatanGroupeSchema(
                        score_cohesion=datan.score_cohesion,
                        score_participation=datan.score_participation,
                        score_majorite=datan.score_majorite,
                        women_pct=datan.women_pct,
                        age_moyen=datan.age_moyen,
                        score_rose=datan.score_rose,
                        position_politique=datan.position_politique,
                    )
                    if datan
                    else None
                ),
            )
        )
    return result


@router.get("/{groupe_id}", response_model=GroupeDetail)
async def get_groupe(
    groupe_id: str,
    session: AsyncSession = Depends(get_session),
) -> GroupeDetail:
    """Détail d'un groupe parlementaire."""
    organe = (
        await session.execute(
            select(Organe)
            .options(selectinload(Organe.deputes))
            .where(Organe.id == groupe_id)
        )
    ).scalar_one_or_none()

    if organe is None:
        raise HTTPException(status_code=404, detail="Groupe introuvable")

    datan = (
        await session.execute(
            select(DatanGroupe).where(DatanGroupe.libelle_abrev == organe.sigle)
        )
    ).scalar_one_or_none()

    deputes_sorted = sorted(
        organe.deputes,
        key=lambda d: (not d.actif, d.nom_de_famille),
    )

    return GroupeDetail(
        id=organe.id,
        sigle=organe.sigle,
        libelle=organe.libelle,
        couleur=organe.couleur,
        nb_deputes=sum(1 for d in organe.deputes if d.actif),
        nb_deputes_total=len(organe.deputes),
        datan=(
            DatanGroupeSchema(
                score_cohesion=datan.score_cohesion,
                score_participation=datan.score_participation,
                score_majorite=datan.score_majorite,
                women_pct=datan.women_pct,
                age_moyen=datan.age_moyen,
                score_rose=datan.score_rose,
                position_politique=datan.position_politique,
            )
            if datan
            else None
        ),
        deputes=[
            DeputeInGroupe(
                id=d.id,
                prenom=d.prenom,
                nom_de_famille=d.nom_de_famille,
                url_photo=d.url_photo,
                num_departement=d.num_departement,
                nom_circonscription=d.nom_circonscription,
                actif=d.actif,
            )
            for d in deputes_sorted
        ],
    )
