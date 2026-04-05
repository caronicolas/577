"""
Ingestion des scores Datan depuis data.gouv.fr.
Datasets : députés actifs + groupes actifs.
Handler Scaleway : handle(event, context)
"""

import asyncio
import csv
import io
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

import httpx
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

GOUV_API = "https://www.data.gouv.fr/api/1/datasets"

DATASET_DEPUTES = "deputes-actifs-de-lassemblee-nationale-informations-et-statistiques"
DATASET_GROUPES = (
    "groupes-politiques-actifs-de-lassemblee-nationale-informations-et-statistiques"
)


# ---------------------------------------------------------------------------
# Retry HTTP
# ---------------------------------------------------------------------------


@retry(
    wait=wait_exponential(min=2, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    r = await client.get(url, follow_redirects=True)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# Résolution URL CSV via l'API data.gouv.fr
# ---------------------------------------------------------------------------


async def _csv_url(client: httpx.AsyncClient, slug: str) -> str:
    """Retourne l'URL du premier fichier CSV du dataset."""
    r = await _get(client, f"{GOUV_API}/{slug}/")
    data = r.json()
    for resource in data.get("resources", []):
        fmt = (resource.get("format") or "").lower()
        mime = (resource.get("mime") or "").lower()
        if fmt == "csv" or "csv" in mime:
            url = resource.get("url") or resource.get("latest")
            if url:
                return url
    raise ValueError(f"Aucun CSV trouvé pour le dataset '{slug}'")


# ---------------------------------------------------------------------------
# Parsing CSV
# ---------------------------------------------------------------------------


def _float(val: str) -> Optional[float]:
    if not val or val.strip() == "":
        return None
    try:
        return float(val.replace(",", "."))
    except ValueError:
        return None


def _date(val: str) -> Optional[datetime]:
    if not val or val.strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_deputes_csv(content: bytes) -> list[dict]:
    rows = []
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    for row in reader:
        identifiant = row.get("id", "").strip()
        if not identifiant.startswith("PA"):
            continue
        rows.append(
            {
                "identifiant_an": identifiant,
                "score_participation": _float(row.get("scoreParticipation", "")),
                "score_participation_specialite": _float(
                    row.get("scoreParticipationSpecialite", "")
                ),
                "score_loyaute": _float(row.get("scoreLoyaute", "")),
                "score_majorite": _float(row.get("scoreMajorite", "")),
                "date_maj": _date(row.get("dateMaj", "")),
            }
        )
    return rows


def parse_groupes_csv(content: bytes) -> list[dict]:
    rows = []
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    for row in reader:
        abrev = row.get("libelleAbrev", "").strip()
        if not abrev:
            continue
        rows.append(
            {
                "libelle_abrev": abrev,
                # Typo dans la source : "socreCohesion" au lieu de "scoreCohesion"
                "score_cohesion": _float(row.get("socreCohesion", "")),
                "score_participation": _float(row.get("scoreParticipation", "")),
                "score_majorite": _float(row.get("scoreMajorite", "")),
                "women_pct": _float(row.get("women", "")),
                "age_moyen": _float(row.get("age", "")),
                "score_rose": _float(row.get("scoreRose", "")),
                "position_politique": row.get("positionPolitique", "").strip() or None,
                "date_maj": _date(row.get("dateMaj", "")),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Connexion DB
# ---------------------------------------------------------------------------


def _get_conn_params() -> dict:
    url = os.environ["DATABASE_URL"]
    url = url.split("://", 1)[1]
    at = url.rfind("@")
    userinfo = url[:at]
    hostinfo = url[at + 1 :]
    user, password = userinfo.split(":", 1) if ":" in userinfo else (userinfo, "")
    slash = hostinfo.find("/")
    hostport, dbname_raw = (
        (hostinfo[:slash], hostinfo[slash + 1 :]) if slash >= 0 else (hostinfo, "")
    )
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
# Upserts
# ---------------------------------------------------------------------------

_UPSERT_DEPUTE = """
INSERT INTO datan_deputes
    (identifiant_an, score_participation, score_participation_specialite,
     score_loyaute, score_majorite, date_maj)
VALUES
    (%(identifiant_an)s, %(score_participation)s,
     %(score_participation_specialite)s, %(score_loyaute)s,
     %(score_majorite)s, %(date_maj)s)
ON CONFLICT (identifiant_an) DO UPDATE SET
    score_participation = EXCLUDED.score_participation,
    score_participation_specialite = EXCLUDED.score_participation_specialite,
    score_loyaute = EXCLUDED.score_loyaute,
    score_majorite = EXCLUDED.score_majorite,
    date_maj = EXCLUDED.date_maj
"""

_UPSERT_GROUPE = """
INSERT INTO datan_groupes
    (libelle_abrev, score_cohesion, score_participation, score_majorite,
     women_pct, age_moyen, score_rose, position_politique, date_maj)
VALUES
    (%(libelle_abrev)s, %(score_cohesion)s, %(score_participation)s,
     %(score_majorite)s, %(women_pct)s, %(age_moyen)s, %(score_rose)s,
     %(position_politique)s, %(date_maj)s)
ON CONFLICT (libelle_abrev) DO UPDATE SET
    score_cohesion = EXCLUDED.score_cohesion,
    score_participation = EXCLUDED.score_participation,
    score_majorite = EXCLUDED.score_majorite,
    women_pct = EXCLUDED.women_pct,
    age_moyen = EXCLUDED.age_moyen,
    score_rose = EXCLUDED.score_rose,
    position_politique = EXCLUDED.position_politique,
    date_maj = EXCLUDED.date_maj
"""


async def _upsert_deputes(conn: psycopg.AsyncConnection, rows: list[dict]) -> int:
    count = 0
    async with conn.transaction():
        for row in rows:
            await conn.execute(_UPSERT_DEPUTE, row)
            count += 1
    return count


async def _upsert_groupes(conn: psycopg.AsyncConnection, rows: list[dict]) -> int:
    count = 0
    async with conn.transaction():
        for row in rows:
            await conn.execute(_UPSERT_GROUPE, row)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run() -> None:
    conn_params = _get_conn_params()

    async with httpx.AsyncClient(timeout=60) as client:
        logger.info("Résolution URL CSV députés actifs…")
        url_deputes = await _csv_url(client, DATASET_DEPUTES)
        logger.info("Téléchargement %s", url_deputes)
        deputes_bytes = (await _get(client, url_deputes)).content

        logger.info("Résolution URL CSV groupes actifs…")
        url_groupes = await _csv_url(client, DATASET_GROUPES)
        logger.info("Téléchargement %s", url_groupes)
        groupes_bytes = (await _get(client, url_groupes)).content

    deputes_rows = parse_deputes_csv(deputes_bytes)
    groupes_rows = parse_groupes_csv(groupes_bytes)
    logger.info("Parsé : %d députés, %d groupes", len(deputes_rows), len(groupes_rows))

    async with await psycopg.AsyncConnection.connect(
        **conn_params, autocommit=True
    ) as conn:
        # Vérifier la jointure avec les députés en base
        known_ids: set[str] = {
            row[0] async for row in await conn.execute("SELECT id FROM deputes")
        }
        missing = [
            r["identifiant_an"]
            for r in deputes_rows
            if r["identifiant_an"] not in known_ids
        ]
        if missing:
            logger.warning(
                "%d identifiants Datan sans correspondance en base : %s",
                len(missing),
                missing[:10],
            )

        nb_dep = await _upsert_deputes(conn, deputes_rows)
        logger.info("Députés upsertés : %d", nb_dep)

        nb_grp = await _upsert_groupes(conn, groupes_rows)
        logger.info("Groupes upsertés : %d", nb_grp)

    logger.info("Ingestion Datan terminée.")


def handle(event, context):
    """Entrypoint Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
    return {"statusCode": 200, "body": "OK"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
