"""
Ingestion des groupes parlementaires depuis data.assemblee-nationale.fr.
Même ZIP que les députés (AMO10) — filtre sur codeType == "GP".
Handler Scaleway : handle(event, context)
"""

import asyncio
import io
import json
import logging
import os
import zipfile
from typing import Optional

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/amo/deputes_actifs_mandats_actifs_organes"
    "/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
)
DATABASE_URL = os.environ["DATABASE_URL"]
LEGISLATURE = 17


# ---------------------------------------------------------------------------
# Modèle Pydantic
# ---------------------------------------------------------------------------


class OrganeNormalise(BaseModel):
    id: str
    sigle: str
    libelle: str
    couleur: Optional[str] = None
    legislature: int = LEGISLATURE


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _normalise_organe(organe: dict) -> OrganeNormalise | None:
    try:
        uid = organe.get("uid")
        if not uid or not isinstance(uid, str):
            return None

        sigle = organe.get("libelleAbrev") or organe.get("libelleAbrege") or ""
        libelle = organe.get("libelle", "")
        if not sigle or not libelle:
            return None

        couleur = organe.get("couleurAssociee")
        # Valider format hex (#rrggbb)
        if couleur and (len(couleur) != 7 or not couleur.startswith("#")):
            couleur = None

        legislature_raw = organe.get("legislature")
        try:
            legislature = int(legislature_raw)
        except (ValueError, TypeError):
            legislature = LEGISLATURE

        return OrganeNormalise(
            id=uid,
            sigle=sigle,
            libelle=libelle,
            couleur=couleur,
            legislature=legislature,
        )
    except Exception:
        logger.warning(
            "Normalisation échouée pour organe %s", organe.get("uid"), exc_info=True
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


def _parse_zip(content: bytes) -> list[OrganeNormalise]:
    organes: list[OrganeNormalise] = []

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        organe_files = [
            n for n in zf.namelist() if "/organe/" in n and n.endswith(".json")
        ]
        logger.info("%d fichiers organe dans le ZIP", len(organe_files))

        for name in organe_files:
            try:
                data = json.loads(zf.read(name))
                organe = data.get("organe", data)
                if organe.get("codeType") != "GP":
                    continue
                o = _normalise_organe(organe)
                if o:
                    organes.append(o)
            except Exception:
                logger.warning("Fichier ignoré : %s", name, exc_info=True)

    return organes


async def fetch_all_organes() -> list[OrganeNormalise]:
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client)

    organes = _parse_zip(content)
    logger.info(
        "%d groupes parlementaires récupérés (législature %d)",
        len(organes),
        LEGISLATURE,
    )
    return organes


# ---------------------------------------------------------------------------
# Upsert PostgreSQL
# ---------------------------------------------------------------------------

_UPSERT = text(
    """
    INSERT INTO organes (id, sigle, libelle, couleur, legislature, updated_at)
    VALUES (:id, :sigle, :libelle, :couleur, :legislature, now())
    ON CONFLICT (id) DO UPDATE SET
        sigle      = EXCLUDED.sigle,
        libelle    = EXCLUDED.libelle,
        couleur    = EXCLUDED.couleur,
        legislature = EXCLUDED.legislature,
        updated_at = now()
"""
)


async def upsert_organes(organes: list[OrganeNormalise]) -> int:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            for organe in organes:
                await session.execute(_UPSERT, organe.model_dump())

    await engine.dispose()
    return len(organes)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion organes — législature %d", LEGISLATURE)
    organes = await fetch_all_organes()
    count = await upsert_organes(organes)
    logger.info("Terminé : %d groupes parlementaires upsertés", count)
    return {"status": "ok", "upserted": count}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
