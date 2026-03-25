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
from datetime import date
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
LEGISLATURE = 17


# ---------------------------------------------------------------------------
# Modèles Pydantic
# ---------------------------------------------------------------------------


class DeputeNormalise(BaseModel):
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
        # sexe absent du JSON — déduit de la civilité
        civ = ident.get("civ", "")
        sexe = "F" if civ.startswith("Mme") else ("M" if civ.startswith("M") else None)

        profession_raw = acteur.get("profession", {})
        profession = (
            profession_raw.get("libelleCourant")
            if isinstance(profession_raw, dict)
            else None
        )

        mandats = _as_list(acteur.get("mandats", {}).get("mandat"))
        mandat_an = _find_mandat_an(mandats)
        groupe_id = _find_groupe_id(mandats)

        num_dept = nom_circo = num_circo = mandat_debut = mandat_fin = None
        place_hemicycle = None

        if mandat_an:
            lieu = mandat_an.get("election", {}).get("lieu", {})
            num_dept = lieu.get("numDepartement")
            nom_circo = lieu.get(
                "departement"
            )  # pas de nomCirconscription dans le JSON
            try:
                num_circo = int(lieu["numCirco"])  # champ réel : numCirco
            except (KeyError, ValueError, TypeError):
                pass

            mandat_debut = _parse_date(mandat_an.get("dateDebut"))
            mandat_fin = _parse_date(mandat_an.get("dateFin"))

            try:
                # placeHemicycle est dans mandature, pas à la racine du mandat
                place_hemicycle = int(mandat_an["mandature"]["placeHemicycle"])
            except (KeyError, ValueError, TypeError):
                pass

        numeric_id = depute_id.removeprefix("PA")
        url_photo = (
            f"https://www.assemblee-nationale.fr/dyn/static/tribun/photos/{numeric_id}.jpg"
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
async def _download_zip(client: httpx.AsyncClient) -> bytes:
    """Télécharge l'archive ZIP des députés en exercice."""
    logger.info("Téléchargement ZIP : %s", ZIP_URL)
    r = await client.get(ZIP_URL, timeout=120, follow_redirects=True)
    r.raise_for_status()
    return r.content


def _parse_zip(content: bytes) -> list[DeputeNormalise]:
    """
    Décompresse le ZIP en mémoire et parse chaque fichier JSON.
    Structure attendue dans le ZIP : un fichier JSON par député,
    avec {"acteur": {...}} comme clé racine.
    """
    deputes: list[DeputeNormalise] = []
    errors = 0

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        json_files = [name for name in zf.namelist() if name.endswith(".json")]
        logger.info("%d fichiers JSON dans le ZIP", len(json_files))

        for name in json_files:
            try:
                data = json.loads(zf.read(name))
                # Chaque fichier a {"acteur": {...}} comme racine
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


# ---------------------------------------------------------------------------
# Upsert PostgreSQL
# ---------------------------------------------------------------------------

_UPSERT = text(
    """
    INSERT INTO deputes (
        id, nom, prenom, nom_de_famille, sexe, date_naissance, profession,
        num_departement, nom_circonscription, num_circonscription,
        place_hemicycle, url_photo, url_an, mandat_debut, mandat_fin,
        legislature, groupe_id, updated_at
    ) VALUES (
        :id, :nom, :prenom, :nom_de_famille, :sexe, :date_naissance, :profession,
        :num_departement, :nom_circonscription, :num_circonscription,
        :place_hemicycle, :url_photo, :url_an, :mandat_debut, :mandat_fin,
        :legislature,
        CASE WHEN EXISTS (SELECT 1 FROM organes WHERE id = :groupe_id)
             THEN :groupe_id ELSE NULL END,
        now()
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
        legislature         = EXCLUDED.legislature,
        groupe_id           = COALESCE(EXCLUDED.groupe_id, deputes.groupe_id),
        updated_at          = now()
"""
)


async def upsert_deputes(deputes: list[DeputeNormalise]) -> int:
    engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            for depute in deputes:
                await session.execute(_UPSERT, depute.model_dump())

    await engine.dispose()
    return len(deputes)


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion députés — législature %d", LEGISLATURE)
    deputes = await fetch_all_deputes()
    count = await upsert_deputes(deputes)
    logger.info("Terminé : %d députés upsertés", count)
    return {"status": "ok", "upserted": count}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
