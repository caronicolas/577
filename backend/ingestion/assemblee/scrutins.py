"""
Ingestion des scrutins et votes nominatifs depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)

Structure du ZIP :
  json/VTANR5L17Vxxxx.json  — un fichier par scrutin
  Racine : {"scrutin": {...}}
  Votes nominatifs dans scrutin.ventilationVotes.organe.groupes.groupe[].vote.decompteNominatif
"""

import asyncio
import io
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/loi/scrutins/Scrutins.json.zip"
)
DATABASE_URL = os.environ["DATABASE_URL"]
LEGISLATURE = 17


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------


class ScrutinNormalise(BaseModel):
    id: str
    numero: int
    titre: str
    date_seance: date
    type_vote: Optional[str] = None
    sort: Optional[str] = None
    nombre_votants: Optional[int] = None
    nombre_pours: Optional[int] = None
    nombre_contres: Optional[int] = None
    nombre_abstentions: Optional[int] = None
    url_an: Optional[str] = None
    legislature: int = LEGISLATURE


@dataclass
class VoteDepute:
    scrutin_id: str
    depute_id: str
    position: str  # pour / contre / abstention / nonVotant


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _int(value: object) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: object) -> list:
    """Normalise str/dict/list en list."""
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    return list(value)


def _extract_votes(scrutin_id: str, ventilation: dict) -> list[VoteDepute]:
    """Extrait tous les votes nominatifs d'un scrutin."""
    votes: list[VoteDepute] = []

    groupes = _as_list(ventilation.get("organe", {}).get("groupes", {}).get("groupe"))

    for groupe in groupes:
        decompte = groupe.get("vote", {}).get("decompteNominatif", {})
        if not decompte:
            continue

        for position, cle in (
            ("pour", "pours"),
            ("contre", "contres"),
            ("abstention", "abstentions"),
            ("nonVotant", "nonVotants"),
        ):
            votants = _as_list(
                (decompte.get(cle) or {}).get("votant")
                if isinstance(decompte.get(cle), dict)
                else decompte.get(cle)
            )
            for v in votants:
                if isinstance(v, dict) and v.get("acteurRef"):
                    votes.append(
                        VoteDepute(
                            scrutin_id=scrutin_id,
                            depute_id=v["acteurRef"],
                            position=position,
                        )
                    )

    return votes


def _normalise_scrutin(
    scrutin: dict,
) -> tuple[ScrutinNormalise, list[VoteDepute]] | None:
    try:
        uid = scrutin.get("uid")
        if not uid:
            return None

        numero = _int(scrutin.get("numero"))
        if numero is None:
            return None

        date_scrutin_raw = scrutin.get("dateScrutin")
        try:
            date_seance = date.fromisoformat(date_scrutin_raw)
        except (TypeError, ValueError):
            return None

        titre = scrutin.get("titre") or ""
        type_vote = scrutin.get("typeVote", {}).get("libelleTypeVote")
        sort = (scrutin.get("sort") or {}).get("code")

        synthese = scrutin.get("syntheseVote", {})
        decompte = synthese.get("decompte", {})

        url_an = f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/votes/{uid}"

        s = ScrutinNormalise(
            id=uid,
            numero=numero,
            titre=titre,
            date_seance=date_seance,
            type_vote=type_vote,
            sort=sort,
            nombre_votants=_int(synthese.get("nombreVotants")),
            nombre_pours=_int(decompte.get("pour")),
            nombre_contres=_int(decompte.get("contre")),
            nombre_abstentions=_int(decompte.get("abstentions")),
            url_an=url_an,
        )

        votes = _extract_votes(uid, scrutin.get("ventilationVotes", {}))
        return s, votes

    except Exception:
        logger.warning(
            "Normalisation échouée pour scrutin %s", scrutin.get("uid"), exc_info=True
        )
        return None


# ---------------------------------------------------------------------------
# Téléchargement ZIP + parsing
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _download_zip(client: httpx.AsyncClient) -> bytes:
    logger.info("Téléchargement ZIP : %s", ZIP_URL)
    r = await client.get(ZIP_URL, timeout=120, follow_redirects=True)
    r.raise_for_status()
    return r.content


def _parse_zip(
    content: bytes,
) -> tuple[list[ScrutinNormalise], list[VoteDepute]]:
    scrutins: list[ScrutinNormalise] = []
    votes: list[VoteDepute] = []
    errors = 0

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("%d fichiers scrutin dans le ZIP", len(json_files))

        for name in json_files:
            try:
                data = json.loads(zf.read(name))
                scrutin = data.get("scrutin", data)
                result = _normalise_scrutin(scrutin)
                if result:
                    s, v = result
                    scrutins.append(s)
                    votes.extend(v)
            except Exception:
                logger.warning("Fichier ignoré : %s", name, exc_info=True)
                errors += 1

    if errors:
        logger.warning("%d fichiers n'ont pas pu être parsés", errors)

    return scrutins, votes


async def fetch_all_scrutins() -> tuple[list[ScrutinNormalise], list[VoteDepute]]:
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client)

    scrutins, votes = _parse_zip(content)
    logger.info(
        "%d scrutins récupérés, %d votes nominatifs (législature %d)",
        len(scrutins),
        len(votes),
        LEGISLATURE,
    )
    return scrutins, votes


# ---------------------------------------------------------------------------
# Upsert PostgreSQL
# ---------------------------------------------------------------------------

_UPSERT_SCRUTIN = text(
    """
    INSERT INTO scrutins (
        id, numero, titre, date_seance, type_vote, sort,
        nombre_votants, nombre_pours, nombre_contres, nombre_abstentions,
        url_an, legislature, updated_at
    ) VALUES (
        :id, :numero, :titre, :date_seance, :type_vote, :sort,
        :nombre_votants, :nombre_pours, :nombre_contres, :nombre_abstentions,
        :url_an, :legislature, now()
    )
    ON CONFLICT (id) DO UPDATE SET
        titre             = EXCLUDED.titre,
        type_vote         = EXCLUDED.type_vote,
        sort              = EXCLUDED.sort,
        nombre_votants    = EXCLUDED.nombre_votants,
        nombre_pours      = EXCLUDED.nombre_pours,
        nombre_contres    = EXCLUDED.nombre_contres,
        nombre_abstentions = EXCLUDED.nombre_abstentions,
        url_an            = EXCLUDED.url_an,
        updated_at        = now()
"""
)

_FETCH_DEPUTE_IDS = text("SELECT id FROM deputes")

_DELETE_VOTES_BATCH = text("DELETE FROM votes_deputes WHERE scrutin_id = ANY(:ids)")

_INSERT_VOTES_BULK = text(
    """
    INSERT INTO votes_deputes (scrutin_id, depute_id, position)
    VALUES (:scrutin_id, :depute_id, :position)
    ON CONFLICT (scrutin_id, depute_id) DO UPDATE SET position = EXCLUDED.position
"""
)


async def _load_depute_ids(session: AsyncSession) -> set[str]:
    result = await session.execute(_FETCH_DEPUTE_IDS)
    return {row[0] for row in result}


async def upsert_scrutins(
    session: AsyncSession,
    scrutins: list[ScrutinNormalise],
) -> None:
    for s in scrutins:
        await session.execute(_UPSERT_SCRUTIN, s.model_dump())


async def persist_all(
    scrutins: list[ScrutinNormalise],
    votes_par_scrutin: dict[str, list[VoteDepute]],
) -> int:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    # 1. Scrutins en un seul commit
    async with Session() as session:
        async with session.begin():
            await upsert_scrutins(session, scrutins)

    # 2. Charger les IDs députés connus pour filtrer en Python (évite les FK errors)
    async with Session() as session:
        depute_ids = await _load_depute_ids(session)
    logger.info("%d députés connus en base pour filtrage des votes", len(depute_ids))

    # 3. Votes par lot de 200 scrutins — bulk insert via executemany
    scrutin_ids = list(votes_par_scrutin.keys())
    batch_size = 200
    total_votes = 0

    for i in range(0, len(scrutin_ids), batch_size):
        batch = scrutin_ids[i : i + batch_size]
        rows = [
            {
                "scrutin_id": v.scrutin_id,
                "depute_id": v.depute_id,
                "position": v.position,
            }
            for sid in batch
            for v in votes_par_scrutin[sid]
            if v.depute_id in depute_ids
        ]
        async with Session() as session:
            async with session.begin():
                # Supprime les votes existants pour ce batch
                await session.execute(_DELETE_VOTES_BATCH, {"ids": batch})
                if rows:
                    await session.execute(_INSERT_VOTES_BULK, rows)
        total_votes += len(rows)
        logger.info(
            "Votes : %d/%d scrutins — %d votes insérés",
            min(i + batch_size, len(scrutin_ids)),
            len(scrutin_ids),
            total_votes,
        )

    await engine.dispose()
    return len(scrutins)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion scrutins — législature %d", LEGISLATURE)

    scrutins, votes = await fetch_all_scrutins()

    # Regroupe les votes par scrutin_id
    votes_par_scrutin: dict[str, list[VoteDepute]] = {}
    for v in votes:
        votes_par_scrutin.setdefault(v.scrutin_id, []).append(v)

    count = await persist_all(scrutins, votes_par_scrutin)
    total_votes = sum(len(v) for v in votes_par_scrutin.values())

    logger.info(
        "Terminé : %d scrutins, %d votes nominatifs upsertés", count, total_votes
    )
    return {"status": "ok", "scrutins": count, "votes": total_votes}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
