from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Amendement, Depute, Scrutin, VoteDepute
from db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------


class GroupeResume(BaseModel):
    id: str
    sigle: str
    libelle: str
    couleur: Optional[str]

    model_config = {"from_attributes": True}


class DeputeListItem(BaseModel):
    id: str
    nom: str
    prenom: str
    num_departement: Optional[str]
    nom_circonscription: Optional[str]
    num_circonscription: Optional[int]
    place_hemicycle: Optional[int]
    url_photo: Optional[str]
    groupe: Optional[GroupeResume]

    model_config = {"from_attributes": True}


class DeputeListResponse(BaseModel):
    total: int
    items: list[DeputeListItem]


class VoteJour(BaseModel):
    scrutin_id: str
    titre: str
    position: str  # pour / contre / abstention / nonVotant


class AmendementJour(BaseModel):
    id: str
    numero: Optional[str]
    titre: Optional[str]
    url_an: Optional[str]


class Activite(BaseModel):
    date: date
    present: bool
    a_vote: bool
    a_pris_parole: bool
    a_depose_amendement: bool
    votes: list[VoteJour]
    amendements: list[AmendementJour]


class ScrutinResume(BaseModel):
    id: str
    numero: int
    titre: str
    date_seance: date
    sort: Optional[str]
    position: str  # pour / contre / abstention / nonVotant


class AmendementResume(BaseModel):
    id: str
    numero: Optional[str]
    titre: Optional[str]
    texte_legislature: Optional[str]
    date_depot: Optional[date]
    sort: Optional[str]
    url_an: Optional[str]


class DeputeDetail(BaseModel):
    id: str
    nom: str
    prenom: str
    nom_de_famille: str
    sexe: Optional[str]
    date_naissance: Optional[date]
    profession: Optional[str]
    num_departement: Optional[str]
    nom_circonscription: Optional[str]
    num_circonscription: Optional[int]
    place_hemicycle: Optional[int]
    url_photo: Optional[str]
    url_an: Optional[str]
    twitter: Optional[str]
    mandat_debut: Optional[date]
    mandat_fin: Optional[date]
    legislature: int
    groupe: Optional[GroupeResume]
    votes: list[ScrutinResume]
    amendements: list[AmendementResume]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=DeputeListResponse)
async def list_deputes(
    groupe: Optional[str] = Query(None, description="Sigle du groupe parlementaire"),
    departement: Optional[str] = Query(None, description="Numéro de département"),
    q: Optional[str] = Query(None, description="Recherche par nom"),
    limit: int = Query(50, ge=1, le=600),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> DeputeListResponse:
    base = (
        select(Depute)
        .options(selectinload(Depute.groupe))
        .where(Depute.mandat_fin.is_(None))
    )
    if groupe:
        base = base.where(Depute.groupe.has(sigle=groupe))
    if departement:
        base = base.where(Depute.num_departement == departement)
    if q:
        base = base.where(Depute.nom.ilike(f"%{q}%"))

    total_result = await session.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar_one()

    stmt = base.order_by(Depute.nom_de_famille).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()

    items = [
        DeputeListItem(
            id=d.id,
            nom=d.nom,
            prenom=d.prenom,
            num_departement=d.num_departement,
            nom_circonscription=d.nom_circonscription,
            num_circonscription=d.num_circonscription,
            place_hemicycle=d.place_hemicycle,
            url_photo=d.url_photo,
            groupe=(
                GroupeResume(
                    id=d.groupe.id,
                    sigle=d.groupe.sigle,
                    libelle=d.groupe.libelle,
                    couleur=d.groupe.couleur,
                )
                if d.groupe
                else None
            ),
        )
        for d in rows
    ]
    return DeputeListResponse(total=total, items=items)


@router.get("/{depute_id}", response_model=DeputeDetail)
async def get_depute(
    depute_id: str,
    votes_limit: int = Query(
        50, ge=1, le=200, description="Nombre de votes à retourner"
    ),
    amendements_limit: int = Query(
        50, ge=1, le=200, description="Nombre d'amendements à retourner"
    ),
    session: AsyncSession = Depends(get_session),
) -> DeputeDetail:
    # Député + groupe
    stmt = (
        select(Depute)
        .options(selectinload(Depute.groupe))
        .where(Depute.id == depute_id)
    )
    depute = (await session.execute(stmt)).scalar_one_or_none()
    if depute is None:
        raise HTTPException(status_code=404, detail="Député introuvable")

    # Votes : jointure avec Scrutin pour avoir les métadonnées, triés par date desc
    votes_stmt = (
        select(VoteDepute, Scrutin)
        .join(Scrutin, VoteDepute.scrutin_id == Scrutin.id)
        .where(VoteDepute.depute_id == depute_id)
        .order_by(Scrutin.date_seance.desc())
        .limit(votes_limit)
    )
    votes_rows = (await session.execute(votes_stmt)).all()

    # Amendements triés par date de dépôt desc
    amendements_stmt = (
        select(Amendement)
        .where(Amendement.depute_id == depute_id)
        .order_by(Amendement.date_depot.desc())
        .limit(amendements_limit)
    )
    amendements = (await session.execute(amendements_stmt)).scalars().all()

    return DeputeDetail(
        id=depute.id,
        nom=depute.nom,
        prenom=depute.prenom,
        nom_de_famille=depute.nom_de_famille,
        sexe=depute.sexe,
        date_naissance=depute.date_naissance,
        profession=depute.profession,
        num_departement=depute.num_departement,
        nom_circonscription=depute.nom_circonscription,
        num_circonscription=depute.num_circonscription,
        place_hemicycle=depute.place_hemicycle,
        url_photo=depute.url_photo,
        url_an=depute.url_an,
        twitter=depute.twitter,
        mandat_debut=depute.mandat_debut,
        mandat_fin=depute.mandat_fin,
        legislature=depute.legislature,
        groupe=(
            GroupeResume(
                id=depute.groupe.id,
                sigle=depute.groupe.sigle,
                libelle=depute.groupe.libelle,
                couleur=depute.groupe.couleur,
            )
            if depute.groupe
            else None
        ),
        votes=[
            ScrutinResume(
                id=scrutin.id,
                numero=scrutin.numero,
                titre=scrutin.titre,
                date_seance=scrutin.date_seance,
                sort=scrutin.sort,
                position=vote.position,
            )
            for vote, scrutin in votes_rows
        ],
        amendements=[
            AmendementResume(
                id=a.id,
                numero=a.numero,
                titre=a.titre,
                texte_legislature=a.texte_legislature,
                date_depot=a.date_depot,
                sort=a.sort,
                url_an=a.url_an,
            )
            for a in amendements
        ],
    )


@router.get("/{depute_id}/activites", response_model=list[Activite])
async def get_activites(
    depute_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[Activite]:
    """
    Retourne l'activité journalière du député sur la 17e législature
    (depuis 2024-06-18). Agrège votes (VoteDepute + Scrutin) et
    amendements (Amendement). Seules les dates avec au moins un
    événement sont retournées.
    """
    depute_exists = (
        await session.execute(select(Depute.id).where(Depute.id == depute_id))
    ).scalar_one_or_none()
    if depute_exists is None:
        raise HTTPException(status_code=404, detail="Député introuvable")

    leg_debut = date(2024, 6, 18)
    today = date.today()

    # -- Votes : date + position + titre scrutin ---------------------------------
    votes_stmt = (
        select(Scrutin.date_seance, Scrutin.id, Scrutin.titre, VoteDepute.position)
        .join(VoteDepute, VoteDepute.scrutin_id == Scrutin.id)
        .where(
            VoteDepute.depute_id == depute_id,
            Scrutin.date_seance >= leg_debut,
            Scrutin.date_seance <= today,
        )
    )
    votes_rows = (await session.execute(votes_stmt)).all()

    # -- Amendements : date + numéro + titre + url -------------------------------
    amend_stmt = select(
        Amendement.id,
        Amendement.date_depot,
        Amendement.numero,
        Amendement.titre,
        Amendement.url_an,
    ).where(
        Amendement.depute_id == depute_id,
        Amendement.date_depot >= leg_debut,
        Amendement.date_depot <= today,
        Amendement.date_depot.is_not(None),
    )
    amend_rows = (await session.execute(amend_stmt)).all()

    # -- Agrégation par date -----------------------------------------------------
    POSITIONS_VOTEES = {"pour", "contre", "abstention"}

    data: dict[date, dict] = defaultdict(
        lambda: {
            "present": False,
            "a_vote": False,
            "a_depose_amendement": False,
            "votes": [],
            "amendements": [],
        }
    )

    for d, scrutin_id, titre, position in votes_rows:
        entry = data[d]
        entry["present"] = True
        if position.lower() in POSITIONS_VOTEES:
            entry["a_vote"] = True
        entry["votes"].append(
            VoteJour(scrutin_id=scrutin_id, titre=titre, position=position)
        )

    for amend_id, d, numero, titre, url_an in amend_rows:
        data[d]["a_depose_amendement"] = True
        data[d]["present"] = True
        data[d]["amendements"].append(
            AmendementJour(id=amend_id, numero=numero, titre=titre, url_an=url_an)
        )

    return [
        Activite(
            date=d,
            present=v["present"],
            a_vote=v["a_vote"],
            a_pris_parole=False,  # pas encore en base
            a_depose_amendement=v["a_depose_amendement"],
            votes=v["votes"],
            amendements=v["amendements"],
        )
        for d, v in sorted(data.items())
    ]
