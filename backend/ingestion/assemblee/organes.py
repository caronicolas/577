"""
Ingestion des organes (groupes parlementaires + commissions).
Source : data.assemblee-nationale.fr — ZIP AMO10.
Handler Scaleway : handle(event, context)
"""

import asyncio
import io
import json
import logging
import os
import zipfile
from typing import Optional
from urllib.parse import unquote

import httpx
import psycopg
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
# Parsing
# ---------------------------------------------------------------------------


def _normalise_organe(organe: dict) -> Optional[dict]:
    try:
        uid = organe.get("uid")
        if not uid or not isinstance(uid, str):
            return None

        sigle = organe.get("libelleAbrev") or organe.get("libelleAbrege") or ""
        libelle = organe.get("libelle", "")
        if not sigle or not libelle:
            return None

        couleur = organe.get("couleurAssociee")
        if couleur and (len(couleur) != 7 or not couleur.startswith("#")):
            couleur = None

        legislature_raw = organe.get("legislature")
        try:
            legislature = int(legislature_raw)
        except (ValueError, TypeError):
            legislature = LEGISLATURE

        return {
            "id": uid,
            "sigle": sigle,
            "libelle": libelle,
            "couleur": couleur,
            "legislature": legislature,
        }
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


def _parse_zip(content: bytes) -> list[dict]:
    organes: list[dict] = []

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        organe_files = [
            n for n in zf.namelist() if "/organe/" in n and n.endswith(".json")
        ]
        logger.info("%d fichiers organe dans le ZIP", len(organe_files))

        for name in organe_files:
            try:
                data = json.loads(zf.read(name))
                organe = data.get("organe", data)
                if not organe.get("codeType"):
                    continue
                o = _normalise_organe(organe)
                if o:
                    organes.append(o)
            except Exception:
                logger.warning("Fichier ignoré : %s", name, exc_info=True)

    return organes


# ---------------------------------------------------------------------------
# Connexion DB (même pattern que les autres fonctions psycopg3)
# ---------------------------------------------------------------------------


def _get_conn_params() -> dict:
    url = DATABASE_URL.split("://", 1)[1]
    at = url.rfind("@")
    userinfo = url[:at]
    hostinfo = url[at + 1 :]
    user, password = userinfo.split(":", 1) if ":" in userinfo else (userinfo, "")
    slash = hostinfo.find("/")
    if slash >= 0:
        hostport, dbname_raw = hostinfo[:slash], hostinfo[slash + 1 :]
    else:
        hostport, dbname_raw = hostinfo, ""
    dbname = dbname_raw.split("?", 1)[0]
    if ":" in hostport:
        colon = hostport.rfind(":")
        host, port = hostport[:colon], int(hostport[colon + 1 :])
    else:
        host, port = hostport, 5432
    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": unquote(user),
        "password": unquote(password),
    }


# ---------------------------------------------------------------------------
# Upsert PostgreSQL
# ---------------------------------------------------------------------------

_UPSERT = """
    INSERT INTO organes (id, sigle, libelle, couleur, legislature, updated_at)
    VALUES (%s, %s, %s, %s, %s, now())
    ON CONFLICT (id) DO UPDATE SET
        sigle       = EXCLUDED.sigle,
        libelle     = EXCLUDED.libelle,
        couleur     = EXCLUDED.couleur,
        legislature = EXCLUDED.legislature,
        updated_at  = now()
"""


async def upsert_organes(organes: list[dict]) -> int:
    conn_params = _get_conn_params()
    BATCH = 500
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        for i in range(0, len(organes), BATCH):
            batch = organes[i : i + BATCH]
            params = [
                (o["id"], o["sigle"], o["libelle"], o["couleur"], o["legislature"])
                for o in batch
            ]
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.executemany(_UPSERT, params)
            logger.info(
                "Upsert %d/%d organes", min(i + BATCH, len(organes)), len(organes)
            )
    return len(organes)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion organes — législature %d", LEGISLATURE)
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client)
    organes = _parse_zip(content)
    logger.info("%d organes parsés", len(organes))
    count = await upsert_organes(organes)
    logger.info("Terminé : %d organes upsertés", count)
    return {"status": "ok", "upserted": count}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
