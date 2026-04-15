from datetime import date
from html import unescape
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Amendement, Depute, Organe
from db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class DeputeResume(BaseModel):
    id: str
    nom: str
    url_photo: Optional[str]
    groupe_sigle: Optional[str]
    groupe_couleur: Optional[str]


class AmendementListItem(BaseModel):
    id: str
    numero: Optional[str]
    titre: Optional[str]
    expose_sommaire: Optional[str]
    texte_legislature: Optional[str]
    date_depot: Optional[date]
    sort: Optional[str]
    url_an: Optional[str]
    depute_id: Optional[str]


class AmendementListResponse(BaseModel):
    total: int
    items: list[AmendementListItem]


class AmendementDetail(BaseModel):
    id: str
    numero: Optional[str]
    titre: Optional[str]
    texte_legislature: Optional[str]
    date_depot: Optional[date]
    sort: Optional[str]
    url_an: Optional[str]
    legislature: int
    depute: Optional[DeputeResume]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=AmendementListResponse)
async def list_amendements(
    depute_id: Optional[str] = Query(None, description="Filtrer par député"),
    texte: Optional[str] = Query(
        None, description="Filtrer par référence de texte législatif"
    ),
    sort: Optional[str] = Query(
        None, description="Filtrer par sort (Adopté, Rejeté, Retiré…)"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> AmendementListResponse:
    base = select(Amendement)
    if depute_id:
        base = base.where(Amendement.depute_id == depute_id)
    if texte:
        base = base.where(Amendement.texte_legislature == texte)
    if sort:
        base = base.where(Amendement.sort.ilike(f"%{sort}%"))

    total = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    stmt = base.order_by(Amendement.date_depot.desc()).limit(limit).offset(offset)
    amendements = (await session.execute(stmt)).scalars().all()

    return AmendementListResponse(
        total=total,
        items=[
            AmendementListItem(
                id=a.id,
                numero=a.numero,
                titre=a.titre,
                expose_sommaire=(
                    unescape(a.expose_sommaire) if a.expose_sommaire else None
                ),
                texte_legislature=a.texte_legislature,
                date_depot=a.date_depot,
                sort=a.sort,
                url_an=a.url_an,
                depute_id=a.depute_id,
            )
            for a in amendements
        ],
    )


@router.get("/{amendement_id}", response_model=AmendementDetail)
async def get_amendement(
    amendement_id: str,
    session: AsyncSession = Depends(get_session),
) -> AmendementDetail:
    # Amendement + député + groupe en une seule requête
    stmt = (
        select(Amendement, Depute, Organe)
        .outerjoin(Depute, Amendement.depute_id == Depute.id)
        .outerjoin(Organe, Depute.groupe_id == Organe.id)
        .where(Amendement.id == amendement_id)
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Amendement introuvable")

    amendement, depute, organe = row

    return AmendementDetail(
        id=amendement.id,
        numero=amendement.numero,
        titre=amendement.titre,
        texte_legislature=amendement.texte_legislature,
        date_depot=amendement.date_depot,
        sort=amendement.sort,
        url_an=amendement.url_an,
        legislature=amendement.legislature,
        depute=(
            DeputeResume(
                id=depute.id,
                nom=depute.nom,
                url_photo=depute.url_photo,
                groupe_sigle=organe.sigle if organe else None,
                groupe_couleur=organe.couleur if organe else None,
            )
            if depute
            else None
        ),
    )
