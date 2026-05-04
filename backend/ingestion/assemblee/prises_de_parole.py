"""
Ingestion des prises de parole en séance plénière depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)

Source : syceron.xml.zip — comptes rendus intégraux (SYCERON)
Structure du ZIP :
  xml/compteRendu/CRSANR5L17S*.xml

Chaque fichier XML contient :
  <uid>           — identifiant du compte rendu
  <seanceRef>     — référence à la séance (RUANR5L17S*IDS*)
  <metadonnees><dateSeance>  — date au format YYYYMMDDHHmmSSmmm
  <paragraphe id_acteur="PA...">  — un paragraphe par prise de parole

On extrait une ligne par (depute_id, seance_id) : un député ne compte
qu'une fois par séance même s'il est intervenu plusieurs fois.
"""

import asyncio
import io
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import date

import httpx
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/vp/syceronbrut/syseron.xml.zip"
)
LEGISLATURE = 17

# Début de la 17e législature
LEG_DEBUT = date(2024, 6, 18)

# Regex compilés une seule fois
_RE_SEANCE_REF = re.compile(r"<seanceRef>([^<]+)</seanceRef>")
_RE_DATE_SEANCE = re.compile(r"<dateSeance>(\d{8})")
_RE_ACTEUR = re.compile(r'id_acteur="(PA\d+)"')


# ---------------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------------


@dataclass
class PrisesSeance:
    seance_id: str
    date: date
    depute_ids: set[str]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@retry(
    wait=wait_exponential(min=2, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _download_zip(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_date(raw: str) -> date | None:
    """Parse YYYYMMDDHHmmSSmmm → date."""
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    except (ValueError, IndexError):
        return None


def parse_compte_rendu(content: bytes) -> PrisesSeance | None:
    text = content.decode("utf-8", errors="replace")

    m_seance = _RE_SEANCE_REF.search(text)
    m_date = _RE_DATE_SEANCE.search(text)

    if not m_seance or not m_date:
        return None

    seance_id = m_seance.group(1).strip()
    # Ne garder que les séances AN (IDS), pas les séances Sénat
    if "IDS" not in seance_id:
        return None

    d = _parse_date(m_date.group(1))
    if not d or d < LEG_DEBUT:
        return None

    depute_ids = set(_RE_ACTEUR.findall(text))
    if not depute_ids:
        return None

    return PrisesSeance(seance_id=seance_id, date=d, depute_ids=depute_ids)


# ---------------------------------------------------------------------------
# DB upsert
# ---------------------------------------------------------------------------


async def upsert_prises(
    conn: psycopg.AsyncConnection,
    prises: list[PrisesSeance],
    known_depute_ids: set[str],
) -> int:
    count = 0
    for p in prises:
        for dep_id in p.depute_ids:
            if dep_id not in known_depute_ids:
                continue
            await conn.execute(
                """
                INSERT INTO prises_de_parole (depute_id, seance_id, date, legislature)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (depute_id, seance_id) DO UPDATE SET
                    date = EXCLUDED.date,
                    legislature = EXCLUDED.legislature
                """,
                (dep_id, p.seance_id, p.date, LEGISLATURE),
            )
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run() -> None:
    database_url = os.environ["DATABASE_URL"]
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    logger.info("Téléchargement du ZIP syceron (%s)…", ZIP_URL)
    zip_bytes = await _download_zip(ZIP_URL)
    logger.info("ZIP téléchargé : %d Mo", len(zip_bytes) // 1_048_576)

    prises: list[PrisesSeance] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
        logger.info("%d fichiers XML dans l'archive", len(xml_files))
        for name in xml_files:
            with zf.open(name) as f:
                result = parse_compte_rendu(f.read())
            if result:
                prises.append(result)

    logger.info("Séances parsées avec prises de parole : %d", len(prises))

    conn_kwargs = dict(
        autocommit=True,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )

    async with await psycopg.AsyncConnection.connect(db_url, **conn_kwargs) as conn:
        known_depute_ids = {
            row[0] async for row in await conn.execute("SELECT id FROM deputes")
        }
        logger.info("%d députés connus en base", len(known_depute_ids))

        BATCH = 50
        total = 0
        for i in range(0, len(prises), BATCH):
            batch = prises[i : i + BATCH]
            async with conn.transaction():
                total += await upsert_prises(conn, batch, known_depute_ids)
            logger.info(
                "Prises insérées/mises à jour : %d (séances %d/%d)",
                total,
                min(i + BATCH, len(prises)),
                len(prises),
            )

    logger.info("Ingestion prises de parole terminée. Total lignes : %d", total)


def handle(event, context):
    """Entrypoint Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
    return {"statusCode": 200, "body": "OK"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
