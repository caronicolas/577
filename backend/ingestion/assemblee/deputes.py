"""
Ingestion des députés en exercice depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)
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
    "/17/amo/deputes_actifs_mandats_actifs_organes"
    "/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
)
ZIP_URL_HISTORIQUE = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/amo/tous_acteurs_mandats_organes_xi_legislature"
    "/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
)
LEGISLATURE = 17


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


@dataclass
class DeputeNormalise:
    id: str
    nom: str
    prenom: str
    nom_de_famille: str
    sexe: Optional[str] = None
    date_naissance: Optional[date] = None
    profession: Optional[str] = None
    num_departement: Optional[str] = None
    nom_circonscription: Optional[str] = None
    num_circonscription: Optional[int] = None
    place_hemicycle: Optional[int] = None
    url_photo: Optional[str] = None
    url_an: Optional[str] = None
    mandat_debut: Optional[date] = None
    mandat_fin: Optional[date] = None
    legislature: int = LEGISLATURE
    groupe_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _as_list(value: object) -> list:
    """Normalise str/dict/list en list (l'AN retourne parfois un seul élément)."""
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    return list(value)


def _find_mandat_an(mandats: list[dict]) -> dict | None:
    for m in mandats:
        if m.get("typeOrgane") == "ASSEMBLEE" and str(m.get("legislature", "")) == str(
            LEGISLATURE
        ):
            return m
    return None


def _find_groupe_id(mandats: list[dict]) -> str | None:
    for m in mandats:
        if m.get("typeOrgane") == "GP" and not m.get("dateFin"):
            refs = _as_list(m.get("organes", {}).get("organeRef"))
            return refs[0] if refs else None
    return None


def _normalise_acteur(acteur: dict) -> DeputeNormalise | None:
    try:
        uid = acteur.get("uid", {})
        depute_id = uid.get("#text", "") if isinstance(uid, dict) else str(uid)
        if not depute_id:
            return None

        ident = acteur.get("etatCivil", {}).get("ident", {})
        info_nais = acteur.get("etatCivil", {}).get("infoNaissance", {})

        prenom = ident.get("prenom", "")
        nom_de_famille = ident.get("nom", "")
        nom = f"{prenom} {nom_de_famille}".strip()
        civ = ident.get("civ", "")
        sexe = "F" if civ.startswith("Mme") else ("M" if civ.startswith("M") else None)

        profession_raw = acteur.get("profession", {})
        profession_val = (
            profession_raw.get("libelleCourant")
            if isinstance(profession_raw, dict)
            else None
        )
        profession = profession_val if isinstance(profession_val, str) else None

        mandats = _as_list(acteur.get("mandats", {}).get("mandat"))
        mandat_an = _find_mandat_an(mandats)
        groupe_id = _find_groupe_id(mandats)

        num_dept = nom_circo = num_circo = mandat_debut = mandat_fin = None
        place_hemicycle = None

        if mandat_an:
            lieu = mandat_an.get("election", {}).get("lieu", {})
            num_dept = lieu.get("numDepartement")
            nom_circo = lieu.get("departement")
            try:
                num_circo = int(lieu["numCirco"])
            except (KeyError, ValueError, TypeError):
                pass

            mandat_debut = _parse_date(mandat_an.get("dateDebut"))
            mandat_fin = _parse_date(mandat_an.get("dateFin"))

            try:
                place_hemicycle = int(mandat_an["mandature"]["placeHemicycle"])
            except (KeyError, ValueError, TypeError):
                pass

        numeric_id = depute_id.removeprefix("PA")
        url_photo = (
            f"https://www.assemblee-nationale.fr/dyn/static/tribun/{LEGISLATURE}/photos/carre/{numeric_id}.jpg"
            if depute_id.startswith("PA")
            else None
        )
        url_an = (
            f"https://www.assemblee-nationale.fr/dyn/{LEGISLATURE}/deputes/{depute_id}"
            if depute_id.startswith("PA")
            else None
        )

        return DeputeNormalise(
            id=depute_id,
            nom=nom,
            prenom=prenom,
            nom_de_famille=nom_de_famille,
            sexe=sexe,
            date_naissance=_parse_date(info_nais.get("dateNais")),
            profession=profession,
            num_departement=num_dept,
            nom_circonscription=nom_circo,
            num_circonscription=num_circo,
            place_hemicycle=place_hemicycle,
            url_photo=url_photo,
            url_an=url_an,
            mandat_debut=mandat_debut,
            mandat_fin=mandat_fin,
            groupe_id=groupe_id,
        )
    except Exception:
        logger.warning(
            "Normalisation échouée pour acteur %s", acteur.get("uid"), exc_info=True
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
async def _download_zip(client: httpx.AsyncClient, url: str = ZIP_URL) -> bytes:
    logger.info("Téléchargement ZIP : %s", url)
    r = await client.get(url, timeout=180, follow_redirects=True)
    r.raise_for_status()
    return r.content


def _parse_zip(content: bytes) -> list[DeputeNormalise]:
    """
    Décompresse le ZIP en mémoire et parse chaque fichier JSON.
    Structure attendue : un fichier JSON par député, {"acteur": {...}}.
    """
    deputes: list[DeputeNormalise] = []
    errors = 0

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        json_files = [name for name in zf.namelist() if name.endswith(".json")]
        logger.info("%d fichiers JSON dans le ZIP", len(json_files))

        for name in json_files:
            try:
                data = json.loads(zf.read(name))
                acteur = data.get("acteur", data)
                d = _normalise_acteur(acteur)
                if d:
                    deputes.append(d)
            except Exception:
                logger.warning("Fichier ignoré : %s", name, exc_info=True)
                errors += 1

    if errors:
        logger.warning("%d fichiers n'ont pas pu être parsés", errors)

    return deputes


async def fetch_all_deputes() -> list[DeputeNormalise]:
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client)

    deputes = _parse_zip(content)
    logger.info("%d députés récupérés (législature %d)", len(deputes), LEGISLATURE)
    return deputes


def _parse_zip_historique(content: bytes) -> list[DeputeNormalise]:
    """Parse le ZIP historique en ne gardant que les acteurs ayant un mandat
    en tant que député dans la 17e législature."""
    deputes: list[DeputeNormalise] = []
    errors = 0

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        json_files = [name for name in zf.namelist() if name.endswith(".json")]
        logger.info("%d fichiers JSON dans le ZIP historique", len(json_files))

        for name in json_files:
            try:
                data = json.loads(zf.read(name))
                acteur = data.get("acteur", data)
                mandats = _as_list(acteur.get("mandats", {}).get("mandat"))
                has_17 = any(
                    m.get("typeOrgane") == "ASSEMBLEE"
                    and str(m.get("legislature", "")) == str(LEGISLATURE)
                    for m in mandats
                )
                if not has_17:
                    continue
                d = _normalise_acteur(acteur)
                if d:
                    deputes.append(d)
            except Exception:
                logger.warning("Fichier historique ignoré : %s", name, exc_info=True)
                errors += 1

    if errors:
        logger.warning("%d fichiers historiques n'ont pas pu être parsés", errors)

    return deputes


async def fetch_deputes_historiques() -> list[DeputeNormalise]:
    async with httpx.AsyncClient() as client:
        content = await _download_zip(client, url=ZIP_URL_HISTORIQUE)

    deputes = _parse_zip_historique(content)
    logger.info(
        "%d ex-députés récupérés depuis le ZIP historique (législature %d)",
        len(deputes),
        LEGISLATURE,
    )
    return deputes


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

    # host:port/dbname
    slash = hostinfo.find("/")
    if slash >= 0:
        hostport, dbname = hostinfo[:slash], hostinfo[slash + 1 :]
    else:
        hostport, dbname = hostinfo, ""

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

_UPSERT = """
    INSERT INTO deputes (
        id, nom, prenom, nom_de_famille, sexe, date_naissance, profession,
        num_departement, nom_circonscription, num_circonscription,
        place_hemicycle, url_photo, url_an, mandat_debut, mandat_fin,
        actif, legislature, groupe_id, updated_at
    ) VALUES (
        %(id)s, %(nom)s, %(prenom)s, %(nom_de_famille)s, %(sexe)s,
        %(date_naissance)s, %(profession)s, %(num_departement)s,
        %(nom_circonscription)s, %(num_circonscription)s, %(place_hemicycle)s,
        %(url_photo)s, %(url_an)s, %(mandat_debut)s, %(mandat_fin)s,
        true, %(legislature)s, %(groupe_id)s, now()
    )
    ON CONFLICT (id) DO UPDATE SET
        nom                 = EXCLUDED.nom,
        prenom              = EXCLUDED.prenom,
        nom_de_famille      = EXCLUDED.nom_de_famille,
        sexe                = EXCLUDED.sexe,
        date_naissance      = EXCLUDED.date_naissance,
        profession          = EXCLUDED.profession,
        num_departement     = EXCLUDED.num_departement,
        nom_circonscription = EXCLUDED.nom_circonscription,
        num_circonscription = EXCLUDED.num_circonscription,
        place_hemicycle     = EXCLUDED.place_hemicycle,
        url_photo           = EXCLUDED.url_photo,
        url_an              = EXCLUDED.url_an,
        mandat_debut        = EXCLUDED.mandat_debut,
        mandat_fin          = EXCLUDED.mandat_fin,
        actif               = true,
        legislature         = EXCLUDED.legislature,
        groupe_id           = COALESCE(EXCLUDED.groupe_id, deputes.groupe_id),
        updated_at          = now()
"""


_INSERT_HISTORIQUE = """
    INSERT INTO deputes (
        id, nom, prenom, nom_de_famille, sexe, date_naissance, profession,
        num_departement, nom_circonscription, num_circonscription,
        place_hemicycle, url_photo, url_an, mandat_debut, mandat_fin,
        actif, legislature, groupe_id, updated_at
    ) VALUES (
        %(id)s, %(nom)s, %(prenom)s, %(nom_de_famille)s, %(sexe)s,
        %(date_naissance)s, %(profession)s, %(num_departement)s,
        %(nom_circonscription)s, %(num_circonscription)s, %(place_hemicycle)s,
        %(url_photo)s, %(url_an)s, %(mandat_debut)s, %(mandat_fin)s,
        false, %(legislature)s, %(groupe_id)s, now()
    )
    ON CONFLICT (id) DO NOTHING
"""


async def upsert_deputes_historiques(deputes: list[DeputeNormalise]) -> int:
    """Insère les ex-députés manquants avec actif=false.
    ON CONFLICT DO NOTHING : ne touche pas aux députés déjà en base (actifs).
    """
    async with await psycopg.AsyncConnection.connect(**_get_conn_params()) as conn:
        rows = await conn.execute("SELECT id FROM organes")
        valid_organe_ids = {r[0] async for r in rows}

        inserted = 0
        for d in deputes:
            groupe_id = d.groupe_id if d.groupe_id in valid_organe_ids else None
            cur = await conn.execute(
                _INSERT_HISTORIQUE,
                {
                    "id": d.id,
                    "nom": d.nom,
                    "prenom": d.prenom,
                    "nom_de_famille": d.nom_de_famille,
                    "sexe": d.sexe,
                    "date_naissance": d.date_naissance,
                    "profession": d.profession,
                    "num_departement": d.num_departement,
                    "nom_circonscription": d.nom_circonscription,
                    "num_circonscription": d.num_circonscription,
                    "place_hemicycle": d.place_hemicycle,
                    "url_photo": d.url_photo,
                    "url_an": d.url_an,
                    "mandat_debut": d.mandat_debut,
                    "mandat_fin": d.mandat_fin,
                    "legislature": d.legislature,
                    "groupe_id": groupe_id,
                },
            )
            inserted += cur.rowcount
        await conn.commit()
        logger.info("%d ex-députés insérés depuis le ZIP historique", inserted)

    return inserted


async def upsert_deputes(deputes: list[DeputeNormalise]) -> int:
    async with await psycopg.AsyncConnection.connect(**_get_conn_params()) as conn:
        # Récupère les IDs d'organes valides pour filtrer en Python (évite
        # le CASE WHEN EXISTS côté SQL qui cause des erreurs psycopg avec
        # les paramètres nommés dans les sous-requêtes).
        rows = await conn.execute("SELECT id FROM organes")
        valid_organe_ids = {r[0] async for r in rows}

        for d in deputes:
            groupe_id = d.groupe_id if d.groupe_id in valid_organe_ids else None
            await conn.execute(
                _UPSERT,
                {
                    "id": d.id,
                    "nom": d.nom,
                    "prenom": d.prenom,
                    "nom_de_famille": d.nom_de_famille,
                    "sexe": d.sexe,
                    "date_naissance": d.date_naissance,
                    "profession": d.profession,
                    "num_departement": d.num_departement,
                    "nom_circonscription": d.nom_circonscription,
                    "num_circonscription": d.num_circonscription,
                    "place_hemicycle": d.place_hemicycle,
                    "url_photo": d.url_photo,
                    "url_an": d.url_an,
                    "mandat_debut": d.mandat_debut,
                    "mandat_fin": d.mandat_fin,
                    "legislature": d.legislature,
                    "groupe_id": groupe_id,
                },
            )
        await conn.commit()

        # Marquer comme inactifs les députés absents du ZIP actifs
        active_ids = [d.id for d in deputes]
        await conn.execute(
            "UPDATE deputes SET actif = false WHERE id != ALL(%(ids)s)",
            {"ids": active_ids},
        )
        inactive_count = (
            await (
                await conn.execute("SELECT COUNT(*) FROM deputes WHERE actif = false")
            ).fetchone()
        )[0]
        await conn.commit()
        logger.info("%d députés marqués inactifs", inactive_count)

    return len(deputes)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion députés — législature %d", LEGISLATURE)

    deputes = await fetch_all_deputes()
    count = await upsert_deputes(deputes)
    logger.info("%d députés actifs upsertés", count)

    deputes_histo = await fetch_deputes_historiques()
    count_histo = await upsert_deputes_historiques(deputes_histo)
    logger.info("%d ex-députés insérés depuis l'historique", count_histo)

    return {"status": "ok", "upserted": count, "historique_inserted": count_histo}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
