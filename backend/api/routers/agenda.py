from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import ReunionCommission, Seance
from db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class PointODJItem(BaseModel):
    ordre: Optional[int]
    titre: Optional[str]


class SeanceItem(BaseModel):
    id: str
    date: date
    titre: Optional[str]
    type_seance: Optional[str]
    is_senat: bool
    points_odj: list[PointODJItem]


class ReunionItem(BaseModel):
    id: str
    date: date
    heure_debut: Optional[str]
    heure_fin: Optional[str]
    titre: Optional[str]
    organe_id: Optional[str]
    organe_libelle: Optional[str]
    is_senat: bool


class JourAgenda(BaseModel):
    date: date
    seances: list[SeanceItem]
    reunions: list[ReunionItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[JourAgenda])
async def get_agenda(
    date_debut: Optional[date] = Query(None, description="Date de début (incluse)"),
    date_fin: Optional[date] = Query(None, description="Date de fin (incluse)"),
    jours: int = Query(
        30, ge=1, le=365, description="Nombre de jours si pas de date_debut"
    ),
    session: AsyncSession = Depends(get_session),
) -> list[JourAgenda]:
    """
    Retourne les séances et réunions de commission par jour.
    Par défaut : les 30 prochains jours (et quelques jours passés pour contexte).
    """
    today = date.today()
    if date_debut is None:
        date_debut = today - timedelta(days=7)
    if date_fin is None:
        date_fin = date_debut + timedelta(days=jours)

    # Séances avec points ODJ
    seances_stmt = (
        select(Seance)
        .options(selectinload(Seance.points_odj))
        .where(Seance.date >= date_debut, Seance.date <= date_fin)
        .order_by(Seance.date, Seance.id)
    )
    seances = (await session.execute(seances_stmt)).scalars().all()

    # Réunions commission
    reunions_stmt = (
        select(ReunionCommission)
        .where(
            ReunionCommission.date >= date_debut,
            ReunionCommission.date <= date_fin,
        )
        .order_by(ReunionCommission.date, ReunionCommission.heure_debut)
    )
    reunions = (await session.execute(reunions_stmt)).scalars().all()

    # Grouper par date
    jours_map: dict[date, dict] = {}

    for s in seances:
        if s.date not in jours_map:
            jours_map[s.date] = {"seances": [], "reunions": []}
        jours_map[s.date]["seances"].append(
            SeanceItem(
                id=s.id,
                date=s.date,
                titre=s.titre,
                type_seance=s.type_seance,
                is_senat=s.is_senat,
                points_odj=[
                    PointODJItem(ordre=p.ordre, titre=p.titre)
                    for p in sorted(s.points_odj, key=lambda x: x.ordre or 0)
                ],
            )
        )

    for r in reunions:
        if r.date not in jours_map:
            jours_map[r.date] = {"seances": [], "reunions": []}
        jours_map[r.date]["reunions"].append(
            ReunionItem(
                id=r.id,
                date=r.date,
                heure_debut=r.heure_debut,
                heure_fin=r.heure_fin,
                titre=r.titre,
                organe_id=r.organe_id,
                organe_libelle=r.organe_libelle,
                is_senat=r.is_senat,
            )
        )

    return [
        JourAgenda(
            date=d,
            seances=v["seances"],
            reunions=v["reunions"],
        )
        for d, v in sorted(jours_map.items())
    ]
