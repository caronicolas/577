from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Scrutin, VoteDepute
from db.session import get_session

router = APIRouter()


class ScrutinListItem(BaseModel):
    id: str
    numero: int
    titre: str
    date_seance: str
    sort: Optional[str]
    nombre_votants: Optional[int]
    nombre_pours: Optional[int]
    nombre_contres: Optional[int]
    nombre_abstentions: Optional[int]


class VoteDeputeItem(BaseModel):
    depute_id: str
    nom: str
    place_hemicycle: Optional[int]
    position: str


class ScrutinDetail(ScrutinListItem):
    type_vote: Optional[str]
    url_an: Optional[str]
    votes: list[VoteDeputeItem]


@router.get("", response_model=list[ScrutinListItem])
async def list_scrutins(
    q: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_session),
) -> list[ScrutinListItem]:
    stmt = select(Scrutin).order_by(Scrutin.date_seance.desc()).limit(limit).offset(offset)
    if q:
        stmt = stmt.where(Scrutin.titre.ilike(f"%{q}%"))

    result = await session.execute(stmt)
    scrutins = result.scalars().all()

    return [
        ScrutinListItem(
            id=s.id,
            numero=s.numero,
            titre=s.titre,
            date_seance=str(s.date_seance),
            sort=s.sort,
            nombre_votants=s.nombre_votants,
            nombre_pours=s.nombre_pours,
            nombre_contres=s.nombre_contres,
            nombre_abstentions=s.nombre_abstentions,
        )
        for s in scrutins
    ]


@router.get("/{scrutin_id}", response_model=ScrutinDetail)
async def get_scrutin(
    scrutin_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScrutinDetail:
    stmt = (
        select(Scrutin)
        .options(selectinload(Scrutin.votes).selectinload(VoteDepute.depute))
        .where(Scrutin.id == scrutin_id)
    )
    result = await session.execute(stmt)
    scrutin = result.scalar_one_or_none()
    if scrutin is None:
        raise HTTPException(status_code=404, detail="Scrutin introuvable")

    return ScrutinDetail(
        id=scrutin.id,
        numero=scrutin.numero,
        titre=scrutin.titre,
        date_seance=str(scrutin.date_seance),
        sort=scrutin.sort,
        type_vote=scrutin.type_vote,
        url_an=scrutin.url_an,
        nombre_votants=scrutin.nombre_votants,
        nombre_pours=scrutin.nombre_pours,
        nombre_contres=scrutin.nombre_contres,
        nombre_abstentions=scrutin.nombre_abstentions,
        votes=[
            VoteDeputeItem(
                depute_id=v.depute_id,
                nom=v.depute.nom if v.depute else v.depute_id,
                place_hemicycle=v.depute.place_hemicycle if v.depute else None,
                position=v.position,
            )
            for v in scrutin.votes
        ],
    )
