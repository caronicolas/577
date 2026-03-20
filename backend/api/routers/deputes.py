from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Depute
from db.session import get_session

router = APIRouter()


class DeputeListItem(BaseModel):
    id: str
    nom: str
    prenom: str
    groupe_sigle: Optional[str]
    groupe_couleur: Optional[str]
    num_departement: Optional[str]
    nom_circonscription: Optional[str]
    place_hemicycle: Optional[int]
    url_photo: Optional[str]

    model_config = {"from_attributes": True}


class DeputeDetail(DeputeListItem):
    sexe: Optional[str]
    profession: Optional[str]
    twitter: Optional[str]
    url_an: Optional[str]
    mandat_debut: Optional[str]
    mandat_fin: Optional[str]


@router.get("", response_model=list[DeputeListItem])
async def list_deputes(
    groupe: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[DeputeListItem]:
    stmt = (
        select(Depute)
        .options(selectinload(Depute.groupe))
        .where(Depute.mandat_fin.is_(None))
        .order_by(Depute.nom_de_famille)
    )
    if groupe:
        stmt = stmt.where(Depute.groupe.has(sigle=groupe))
    if departement:
        stmt = stmt.where(Depute.num_departement == departement)
    if q:
        stmt = stmt.where(Depute.nom.ilike(f"%{q}%"))

    result = await session.execute(stmt)
    deputes = result.scalars().all()

    return [
        DeputeListItem(
            id=d.id,
            nom=d.nom,
            prenom=d.prenom,
            groupe_sigle=d.groupe.sigle if d.groupe else None,
            groupe_couleur=d.groupe.couleur if d.groupe else None,
            num_departement=d.num_departement,
            nom_circonscription=d.nom_circonscription,
            place_hemicycle=d.place_hemicycle,
            url_photo=d.url_photo,
        )
        for d in deputes
    ]


@router.get("/{depute_id}", response_model=DeputeDetail)
async def get_depute(
    depute_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeputeDetail:
    stmt = (
        select(Depute)
        .options(selectinload(Depute.groupe))
        .where(Depute.id == depute_id)
    )
    result = await session.execute(stmt)
    depute = result.scalar_one_or_none()
    if depute is None:
        raise HTTPException(status_code=404, detail="Député introuvable")

    return DeputeDetail(
        id=depute.id,
        nom=depute.nom,
        prenom=depute.prenom,
        groupe_sigle=depute.groupe.sigle if depute.groupe else None,
        groupe_couleur=depute.groupe.couleur if depute.groupe else None,
        num_departement=depute.num_departement,
        nom_circonscription=depute.nom_circonscription,
        place_hemicycle=depute.place_hemicycle,
        url_photo=depute.url_photo,
        sexe=depute.sexe,
        profession=depute.profession,
        twitter=depute.twitter,
        url_an=depute.url_an,
        mandat_debut=str(depute.mandat_debut) if depute.mandat_debut else None,
        mandat_fin=str(depute.mandat_fin) if depute.mandat_fin else None,
    )
