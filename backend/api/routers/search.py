from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Depute, Organe, Scrutin
from db.session import get_session

router = APIRouter()


class DeputeResult(BaseModel):
    type: str = "depute"
    id: str
    nom: str
    prenom: str
    groupe_sigle: Optional[str]
    groupe_couleur: Optional[str]
    url_photo: Optional[str]


class ScrutinResult(BaseModel):
    type: str = "scrutin"
    id: str
    titre: str
    date_seance: date
    sort: Optional[str]


class SearchResponse(BaseModel):
    deputes: list[DeputeResult]
    scrutins: list[ScrutinResult]


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    pattern = f"%{q}%"

    deputes_stmt = (
        select(Depute, Organe)
        .outerjoin(Organe, Depute.groupe_id == Organe.id)
        .where(
            Depute.actif.is_(True),
            or_(
                Depute.nom.ilike(pattern),
                Depute.prenom.ilike(pattern),
                func.concat(Depute.prenom, " ", Depute.nom).ilike(pattern),
            ),
        )
        .order_by(Depute.nom)
        .limit(6)
    )
    scrutins_stmt = (
        select(Scrutin)
        .where(Scrutin.titre.ilike(pattern))
        .order_by(Scrutin.date_seance.desc())
        .limit(5)
    )

    deputes_rows = (await session.execute(deputes_stmt)).all()
    scrutins_rows = (await session.execute(scrutins_stmt)).scalars().all()

    return SearchResponse(
        deputes=[
            DeputeResult(
                id=d.id,
                nom=d.nom,
                prenom=d.prenom,
                groupe_sigle=o.sigle if o else None,
                groupe_couleur=o.couleur if o else None,
                url_photo=d.url_photo,
            )
            for d, o in deputes_rows
        ],
        scrutins=[
            ScrutinResult(
                id=s.id,
                titre=s.titre,
                date_seance=s.date_seance,
                sort=s.sort,
            )
            for s in scrutins_rows
        ],
    )
