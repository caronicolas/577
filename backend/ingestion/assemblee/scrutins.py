"""
Ingestion des scrutins et votes nominatifs depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)

Structure du ZIP :
  json/VTANR5L17Vxxxx.json  — un fichier par scrutin
  Racine : {"scrutin": {...}}
  Votes nominatifs dans scrutin.ventilationVotes.organe.groupes
  .groupe[].vote.decompteNominatif
"""

import asyncio
import io
import json
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import date
from typing import Optional
from urllib.parse import unquote

import httpx
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/loi/scrutins/Scrutins.json.zip"
)
LEGISLATURE = 17


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


@dataclass
class ScrutinNormalise:
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
    ref_amendement: Optional[str] = None
    objet_libelle: Optional[str] = None
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
            votants = _as_list((decompte.get(cle) or {}).get("votant"))
            for votant in votants:
                depute_ref = votant.get("acteurRef", "")
                if depute_ref:
                    votes.append(
                        VoteDepute(
                            scrutin_id=scrutin_id,
                            depute_id=depute_ref,
                            position=position,
                        )
                    )

    return votes


def _normalise_scrutin(
    scrutin: dict,
) -> Optional[tuple["ScrutinNormalise", list[VoteDepute]]]:
    try:
        uid = scrutin.get("uid", "")
        if not uid:
            return None

        synthese = scrutin.get("syntheseVote", {})
        decompte = synthese.get("decompte", {})

        numero_raw = scrutin.get("numero", "")
        try:
            numero = int(numero_raw)
        except (TypeError, ValueError):
            return None

        titre = scrutin.get("titre", "").strip() or f"Scrutin n°{numero}"

        date_seance_raw = scrutin.get("dateScrutin", "")
        try:
            date_seance = date.fromisoformat(str(date_seance_raw)[:10])
        except (ValueError, TypeError):
            return None

        type_vote = scrutin.get("typeVote", {}).get("libelleTypeVote")
        sort = scrutin.get("sort", {}).get("code")

        url_an = (
            f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/scrutins/{numero}"
        )

        objet = scrutin.get("objet") or {}
        ref_amendement = (objet.get("amendement") or {}).get("refAmendement") or None
        if isinstance(ref_amendement, dict):  # xsi:nil node
            ref_amendement = None
        objet_libelle_raw = objet.get("libelle")
        objet_libelle = (
            str(objet_libelle_raw).strip()
            if objet_libelle_raw and not isinstance(objet_libelle_raw, dict)
            else None
        )

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
            ref_amendement=ref_amendement,
            objet_libelle=objet_libelle,
        )

        votes = _extract_votes(uid, scrutin.get("ventilationVotes", {}))
        return s, votes

    except Exception:
        logger.warning(
            "Normalisation échouée pour scrutin %s",
            scrutin.get("uid"),
            exc_info=True,
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
# Connexion DB
# ---------------------------------------------------------------------------


def _get_conn_params() -> dict:
    """Parse DATABASE_URL → kwargs pour psycopg.AsyncConnection.connect().

    Parsing manuel avec rfind('@') pour gérer les mots de passe contenant
    des caractères spéciaux ('@', '$', etc.) sans dépendre de urlparse.
    """
    url = os.environ["DATABASE_URL"]
    # Strip driver prefix : postgresql+asyncpg:// → postgresql://
    url = url.split("://", 1)[1]  # retire le schème complet

    # Sépare user:pass de host:port/db en cherchant le DERNIER @
    at = url.rfind("@")
    userinfo = url[:at]
    hostinfo = url[at + 1 :]

    # user:pass
    if ":" in userinfo:
        user, password = userinfo.split(":", 1)
    else:
        user, password = userinfo, ""

    # host:port/dbname?params
    slash = hostinfo.find("/")
    if slash >= 0:
        hostport, dbname_raw = hostinfo[:slash], hostinfo[slash + 1 :]
    else:
        hostport, dbname_raw = hostinfo, ""
    # Strip query string from dbname (e.g. "an577?ssl=require" → "an577")
    dbname = dbname_raw.split("?", 1)[0]

    # host:port
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

_UPSERT_SCRUTIN = """
    INSERT INTO scrutins (
        id, numero, titre, date_seance, type_vote, sort,
        nombre_votants, nombre_pours, nombre_contres, nombre_abstentions,
        url_an, ref_amendement, objet_libelle, legislature, updated_at
    ) VALUES (
        %(id)s, %(numero)s, %(titre)s, %(date_seance)s, %(type_vote)s, %(sort)s,
        %(nombre_votants)s, %(nombre_pours)s, %(nombre_contres)s,
        %(nombre_abstentions)s, %(url_an)s, %(ref_amendement)s,
        %(objet_libelle)s, %(legislature)s, now()
    )
    ON CONFLICT (id) DO UPDATE SET
        titre              = EXCLUDED.titre,
        type_vote          = EXCLUDED.type_vote,
        sort               = EXCLUDED.sort,
        nombre_votants     = EXCLUDED.nombre_votants,
        nombre_pours       = EXCLUDED.nombre_pours,
        nombre_contres     = EXCLUDED.nombre_contres,
        nombre_abstentions = EXCLUDED.nombre_abstentions,
        url_an             = EXCLUDED.url_an,
        ref_amendement     = EXCLUDED.ref_amendement,
        objet_libelle      = EXCLUDED.objet_libelle,
        updated_at         = now()
"""


async def persist_all(
    scrutins: list[ScrutinNormalise],
    votes_par_scrutin: dict[str, list[VoteDepute]],
) -> int:
    conn_params = _get_conn_params()

    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        # 1. Upsert scrutins
        for s in scrutins:
            await conn.execute(
                _UPSERT_SCRUTIN,
                {
                    "id": s.id,
                    "numero": s.numero,
                    "titre": s.titre,
                    "date_seance": s.date_seance,
                    "type_vote": s.type_vote,
                    "sort": s.sort,
                    "nombre_votants": s.nombre_votants,
                    "nombre_pours": s.nombre_pours,
                    "nombre_contres": s.nombre_contres,
                    "nombre_abstentions": s.nombre_abstentions,
                    "url_an": s.url_an,
                    "ref_amendement": s.ref_amendement,
                    "objet_libelle": s.objet_libelle,
                    "legislature": s.legislature,
                },
            )
        await conn.commit()
        logger.info("%d scrutins upsertés", len(scrutins))

        # 2. Charger les IDs députés connus pour filtrer (évite les FK errors)
        cur = await conn.execute("SELECT id FROM deputes")
        depute_ids = {row[0] for row in await cur.fetchall()}
        logger.info(
            "%d députés connus en base pour filtrage des votes", len(depute_ids)
        )

        # 3. Votes : DELETE + COPY (beaucoup plus rapide qu'executemany)
        all_scrutin_ids = list(votes_par_scrutin.keys())
        await conn.execute(
            "DELETE FROM votes_deputes WHERE scrutin_id = ANY(%(ids)s)",
            {"ids": all_scrutin_ids},
        )
        # Prépare le buffer COPY en mémoire (1 seul write I/O)
        lines = []
        for sid in all_scrutin_ids:
            for v in votes_par_scrutin[sid]:
                if v.depute_id in depute_ids:
                    lines.append(f"{v.scrutin_id}\t{v.depute_id}\t{v.position}\n")
        total_votes = len(lines)
        cur = conn.cursor()
        async with cur.copy(
            "COPY votes_deputes (scrutin_id, depute_id, position) FROM STDIN"
        ) as copy:
            await copy.write("".join(lines).encode())
        await conn.commit()
        logger.info("%d votes nominatifs insérés via COPY", total_votes)

    return len(scrutins)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion scrutins — législature %d", LEGISLATURE)

    scrutins, votes = await fetch_all_scrutins()

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
