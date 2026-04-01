from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Depute, Organe, Scrutin, VoteDepute
from db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class ScrutinListItem(BaseModel):
    id: str
    numero: int
    titre: str
    date_seance: date
    sort: Optional[str]
    nombre_votants: Optional[int]
    nombre_pours: Optional[int]
    nombre_contres: Optional[int]
    nombre_abstentions: Optional[int]
    position: Optional[str] = None  # présent uniquement quand filtré par depute_id


class ScrutinListResponse(BaseModel):
    total: int
    items: list[ScrutinListItem]


class VoteDeputeItem(BaseModel):
    depute_id: str
    nom: str
    groupe_id: Optional[str]
    groupe_sigle: Optional[str]
    groupe_couleur: Optional[str]
    place_hemicycle: Optional[int]
    position: str  # pour / contre / abstention / nonVotant


class ScrutinDetail(BaseModel):
    id: str
    numero: int
    titre: str
    date_seance: date
    type_vote: Optional[str]
    sort: Optional[str]
    nombre_votants: Optional[int]
    nombre_pours: Optional[int]
    nombre_contres: Optional[int]
    nombre_abstentions: Optional[int]
    url_an: Optional[str]
    expose_sommaire: Optional[str] = None
    legislature: int
    votes: list[VoteDeputeItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ScrutinListResponse)
async def list_scrutins(
    q: Optional[str] = Query(None, description="Recherche dans le titre"),
    depute_id: Optional[str] = Query(
        None, description="Filtrer par député (retourne sa position)"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ScrutinListResponse:
    if depute_id:
        # Jointure avec VoteDepute pour filtrer et récupérer la position
        base = (
            select(Scrutin, VoteDepute.position)
            .join(VoteDepute, VoteDepute.scrutin_id == Scrutin.id)
            .where(VoteDepute.depute_id == depute_id)
        )
        if q:
            base = base.where(Scrutin.titre.ilike(f"%{q}%"))

        total = (
            await session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = (
            await session.execute(
                base.order_by(Scrutin.date_seance.desc()).limit(limit).offset(offset)
            )
        ).all()

        return ScrutinListResponse(
            total=total,
            items=[
                ScrutinListItem(
                    id=s.id,
                    numero=s.numero,
                    titre=s.titre,
                    date_seance=s.date_seance,
                    sort=s.sort,
                    nombre_votants=s.nombre_votants,
                    nombre_pours=s.nombre_pours,
                    nombre_contres=s.nombre_contres,
                    nombre_abstentions=s.nombre_abstentions,
                    position=position,
                )
                for s, position in rows
            ],
        )

    # Pas de filtre depute_id : liste générale
    base_q = select(Scrutin)
    if q:
        base_q = base_q.where(Scrutin.titre.ilike(f"%{q}%"))

    total = (
        await session.execute(select(func.count()).select_from(base_q.subquery()))
    ).scalar_one()

    scrutins = (
        (
            await session.execute(
                base_q.order_by(Scrutin.date_seance.desc()).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )

    return ScrutinListResponse(
        total=total,
        items=[
            ScrutinListItem(
                id=s.id,
                numero=s.numero,
                titre=s.titre,
                date_seance=s.date_seance,
                sort=s.sort,
                nombre_votants=s.nombre_votants,
                nombre_pours=s.nombre_pours,
                nombre_contres=s.nombre_contres,
                nombre_abstentions=s.nombre_abstentions,
            )
            for s in scrutins
        ],
    )


@router.get("/{scrutin_id}", response_model=ScrutinDetail)
async def get_scrutin(
    scrutin_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScrutinDetail:
    row = (
        await session.execute(select(Scrutin).where(Scrutin.id == scrutin_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Scrutin introuvable")
    scrutin = row
    expose_sommaire = scrutin.objet_libelle

    # Votes avec infos député et groupe en une seule requête (pas de N+1)
    votes_stmt = (
        select(VoteDepute, Depute, Organe)
        .join(Depute, VoteDepute.depute_id == Depute.id)
        .outerjoin(Organe, Depute.groupe_id == Organe.id)
        .where(VoteDepute.scrutin_id == scrutin_id)
        .order_by(Depute.place_hemicycle)
    )
    votes_rows = (await session.execute(votes_stmt)).all()

    return ScrutinDetail(
        id=scrutin.id,
        numero=scrutin.numero,
        titre=scrutin.titre,
        date_seance=scrutin.date_seance,
        type_vote=scrutin.type_vote,
        sort=scrutin.sort,
        nombre_votants=scrutin.nombre_votants,
        nombre_pours=scrutin.nombre_pours,
        nombre_contres=scrutin.nombre_contres,
        nombre_abstentions=scrutin.nombre_abstentions,
        url_an=scrutin.url_an,
        expose_sommaire=expose_sommaire,
        legislature=scrutin.legislature,
        votes=[
            VoteDeputeItem(
                depute_id=vote.depute_id,
                nom=depute.nom,
                groupe_id=organe.id if organe else None,
                groupe_sigle=organe.sigle if organe else None,
                groupe_couleur=organe.couleur if organe else None,
                place_hemicycle=depute.place_hemicycle,
                position=vote.position,
            )
            for vote, depute, organe in votes_rows
        ],
    )
