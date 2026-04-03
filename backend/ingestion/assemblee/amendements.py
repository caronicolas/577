"""
Ingestion des amendements depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)

Structure du ZIP :
  json/{dossier}/{texte}/{uid}.json  — un fichier par amendement
  Racine : {"amendement": {...}}
"""

import asyncio
import io
import json
import logging
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from urllib.parse import unquote

import httpx
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/loi/amendements_div_legis/Amendements.json.zip"
)
LEGISLATURE = 17

_HTML_TAG = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------------


@dataclass
class AmendementNormalise:
    id: str
    numero: Optional[str] = None
    titre: Optional[str] = None
    texte_legislature: Optional[str] = None
    dossier_ref: Optional[str] = None
    date_depot: Optional[date] = None
    sort: Optional[str] = None
    expose_sommaire: Optional[str] = None
    url_an: Optional[str] = None
    depute_id: Optional[str] = None
    legislature: int = field(default=LEGISLATURE)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    return _HTML_TAG.sub("", value).strip() or None


def _nil(value: object) -> bool:
    """Retourne True si la valeur est un nœud xsi:nil."""
    return isinstance(value, dict) and value.get("@xsi:nil") == "true"


def _normalise_amendement(
    amend: dict, dossier_ref: str | None = None
) -> AmendementNormalise | None:
    try:
        uid = amend.get("uid")
        if not uid:
            return None

        identification = amend.get("identification", {})
        numero = identification.get("numeroLong") or identification.get(
            "numeroOrdreDepot"
        )

        # Titre = article visé par l'amendement
        division = amend.get("pointeurFragmentTexte", {}).get("division", {})
        titre = division.get("titre") or division.get("articleDesignation")

        texte_legislature = amend.get("texteLegislatifRef")
        if _nil(texte_legislature):
            texte_legislature = None

        cycle = amend.get("cycleDeVie", {})
        date_depot_raw = cycle.get("dateDepot")
        try:
            date_depot = (
                date.fromisoformat(str(date_depot_raw)[:10]) if date_depot_raw else None
            )
        except (ValueError, TypeError):
            date_depot = None

        sort = cycle.get("sort")
        if _nil(sort):
            sort = None

        url_an = (
            f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/amendements/{uid}"
        )

        # Auteur : seulement si c'est un député (pas le gouvernement)
        auteur = amend.get("signataires", {}).get("auteur", {})
        depute_id = None
        if isinstance(auteur, dict) and auteur.get("typeAuteur") == "Député":
            ref = auteur.get("acteurRef")
            if ref and not _nil(ref):
                depute_id = ref

        corps = amend.get("corps") or {}
        contenu_auteur = corps.get("contenuAuteur") or {}
        expose_sommaire = _strip_html(contenu_auteur.get("exposeSommaire"))

        return AmendementNormalise(
            id=uid,
            numero=numero,
            titre=titre,
            texte_legislature=texte_legislature,
            dossier_ref=dossier_ref,
            date_depot=date_depot,
            sort=sort,
            expose_sommaire=expose_sommaire,
            url_an=url_an,
            depute_id=depute_id,
        )
    except Exception:
        logger.warning(
            "Normalisation échouée pour amendement %s", amend.get("uid"), exc_info=True
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
    r = await client.get(ZIP_URL, timeout=300, follow_redirects=True)
    r.raise_for_status()
    return r.content


def _parse_zip(content: bytes) -> list[AmendementNormalise]:
    amendements: list[AmendementNormalise] = []
    errors = 0

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("%d fichiers amendement dans le ZIP", len(json_files))

        for name in json_files:
            try:
                data = json.loads(zf.read(name))
                amend = data.get("amendement", data)
                parts = name.split("/")
                dossier_ref = parts[1] if len(parts) >= 3 else None
                a = _normalise_amendement(amend, dossier_ref=dossier_ref)
                if a:
                    amendements.append(a)
            except Exception:
                logger.warning("Fichier ignoré : %s", name, exc_info=True)
                errors += 1

    if errors:
        logger.warning("%d fichiers n'ont pas pu être parsés", errors)

    return amendements


async def fetch_all_amendements() -> list[AmendementNormalise]:
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client)

    amendements = _parse_zip(content)
    logger.info(
        "%d amendements récupérés (législature %d)",
        len(amendements),
        LEGISLATURE,
    )
    return amendements


# ---------------------------------------------------------------------------
# Connexion DB
# ---------------------------------------------------------------------------


def _get_conn_params() -> dict:
    """Parse DATABASE_URL → kwargs pour psycopg.AsyncConnection.connect()."""
    url = os.environ["DATABASE_URL"]
    url = url.split("://", 1)[1]

    at = url.rfind("@")
    userinfo = url[:at]
    hostinfo = url[at + 1 :]

    if ":" in userinfo:
        user, password = userinfo.split(":", 1)
    else:
        user, password = userinfo, ""

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
    INSERT INTO amendements (
        id, numero, titre, texte_legislature, dossier_ref, date_depot, sort,
        expose_sommaire, url_an, depute_id, legislature, updated_at
    ) VALUES (
        %(id)s, %(numero)s, %(titre)s, %(texte_legislature)s, %(dossier_ref)s,
        %(date_depot)s, %(sort)s, %(expose_sommaire)s, %(url_an)s,
        %(depute_id)s, %(legislature)s, now()
    )
    ON CONFLICT (id) DO UPDATE SET
        numero            = EXCLUDED.numero,
        titre             = EXCLUDED.titre,
        texte_legislature = EXCLUDED.texte_legislature,
        dossier_ref       = EXCLUDED.dossier_ref,
        date_depot        = EXCLUDED.date_depot,
        sort              = EXCLUDED.sort,
        expose_sommaire   = EXCLUDED.expose_sommaire,
        url_an            = EXCLUDED.url_an,
        depute_id         = EXCLUDED.depute_id,
        updated_at        = now()
"""


async def persist_all(
    amendements: list[AmendementNormalise],
    depute_ids: set[str],
    batch_size: int = 500,
) -> int:
    conn_params = _get_conn_params()

    total = 0
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        for i in range(0, len(amendements), batch_size):
            batch = amendements[i : i + batch_size]
            rows = []
            for a in batch:
                rows.append(
                    {
                        "id": a.id,
                        "numero": a.numero,
                        "titre": a.titre,
                        "texte_legislature": a.texte_legislature,
                        "dossier_ref": a.dossier_ref,
                        "date_depot": a.date_depot,
                        "sort": a.sort,
                        "expose_sommaire": a.expose_sommaire,
                        "url_an": a.url_an,
                        "depute_id": a.depute_id if a.depute_id in depute_ids else None,
                        "legislature": a.legislature,
                    }
                )
            await conn.executemany(_UPSERT, rows)
            await conn.commit()
            total += len(rows)
            logger.info(
                "Amendements : %d/%d traités",
                min(i + batch_size, len(amendements)),
                len(amendements),
            )

    return total


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion amendements — législature %d", LEGISLATURE)

    amendements = await fetch_all_amendements()

    conn_params = _get_conn_params()
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        cur = await conn.execute("SELECT id FROM deputes")
        depute_ids = {row[0] for row in await cur.fetchall()}
    logger.info("%d députés connus en base", len(depute_ids))

    count = await persist_all(amendements, depute_ids)
    logger.info("Terminé : %d amendements upsertés", count)
    return {"status": "ok", "upserted": count}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
