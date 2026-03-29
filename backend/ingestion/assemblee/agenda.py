"""
Ingestion de l'agenda (séances + commissions) depuis data.assemblee-nationale.fr.
Handler Scaleway : handle(event, context)

Structure du ZIP :
  json/RUANR5L17Sxxxx.json  — séances plénières (seance_type)
  json/RUANR5L17Cxxxx.json  — réunions de commission (reunionCommission_type)

Champ discriminant : xsi:type dans reunion.cycleDeVie (ou absent pour commissions)
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
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ZIP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository"
    "/17/vp/reunions/Agenda.json.zip"
)
LEGISLATURE = 17

# UID préfixe Sénat ou organe Sénat
SENAT_ORGANE_REF = "PO78718"


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


@dataclass
class SeanceNorm:
    id: str
    date: date
    titre: Optional[str] = None
    type_seance: Optional[str] = None
    is_senat: bool = False
    legislature: int = LEGISLATURE
    points_odj: list[str] = field(default_factory=list)  # titres des points ODJ


@dataclass
class ReunionCommissionNorm:
    id: str
    date: date
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    titre: Optional[str] = None
    organe_id: Optional[str] = None
    organe_libelle: Optional[str] = None
    is_senat: bool = False
    legislature: int = LEGISLATURE
    depute_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Retry HTTP
# ---------------------------------------------------------------------------


@retry(
    wait=wait_exponential(min=2, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _download_zip(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _safe_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None


def _extract_points_odj(odj_data) -> list[str]:
    """Extrait les titres des points ODJ (peut être dict ou liste)."""
    if not odj_data:
        return []
    if isinstance(odj_data, dict):
        odj_data = [odj_data]
    if not isinstance(odj_data, list):
        return []
    titres = []
    for point in odj_data:
        if not isinstance(point, dict):
            continue
        # resumeODJ peut être string ou dict avec #text
        resume = point.get("resumeODJ")
        if resume is None:
            resume = point.get("libelle")
        if isinstance(resume, dict):
            resume = resume.get("#text") or resume.get("@libelle")
        titre = _safe_str(resume)
        if titre:
            titres.append(titre)
    return titres


def _extract_depute_ids(participants_data) -> list[str]:
    """Extrait les IDs des députés participants (acteurRef avec préfixe PA)."""
    if not participants_data:
        return []
    if isinstance(participants_data, dict):
        participants_data = [participants_data]
    if not isinstance(participants_data, list):
        return []
    ids = []
    for p in participants_data:
        if not isinstance(p, dict):
            continue
        acteur_ref = p.get("acteurRef") or p.get("acteur", {}).get("acteurRef")
        if isinstance(acteur_ref, dict):
            acteur_ref = acteur_ref.get("#text")
        ref = _safe_str(acteur_ref)
        if ref and ref.startswith("PA"):
            ids.append(ref)
    return ids


def _is_senat(reunion_data: dict) -> bool:
    """Détermine si c'est une réunion du Sénat."""
    uid = reunion_data.get("uid", "")
    if isinstance(uid, str) and "RUSN" in uid:
        return True
    organe_ref = reunion_data.get("organeRef") or reunion_data.get("organeReunionRef")
    if isinstance(organe_ref, str) and SENAT_ORGANE_REF in organe_ref:
        return True
    return False


def parse_seance(data: dict) -> Optional[SeanceNorm]:
    """Parse un fichier séance_type."""
    reunion = data.get("reunion") or data
    uid = _safe_str(reunion.get("uid"))
    if not uid:
        return None

    # Date depuis cycleDeVie.dateDebut ou dateSeance
    cycle = reunion.get("cycleDeVie") or {}
    date_str = (
        cycle.get("dateDebut") or reunion.get("dateSeance") or reunion.get("date")
    )
    d = _parse_date(date_str)
    if not d:
        return None

    is_senat = _is_senat(reunion)

    # Titre : libelleAbrev ou intitule ou libelle
    titre = _safe_str(
        reunion.get("libelleAbrev") or reunion.get("intitule") or reunion.get("libelle")
    )

    type_seance = _safe_str(
        reunion.get("xsi:type") or reunion.get("typeSeance") or cycle.get("etat")
    )

    # Points ODJ
    odj_raw = reunion.get("ordre_du_jour") or reunion.get("pointsODJ") or {}
    if isinstance(odj_raw, dict):
        points_list = odj_raw.get("pointODJ") or odj_raw.get("point") or []
    else:
        points_list = odj_raw
    if not isinstance(points_list, list):
        points_list = [points_list] if points_list else []
    points = _extract_points_odj(points_list)

    return SeanceNorm(
        id=uid,
        date=d,
        titre=titre,
        type_seance=type_seance,
        is_senat=is_senat,
        legislature=LEGISLATURE,
        points_odj=points,
    )


def parse_reunion_commission(data: dict) -> Optional[ReunionCommissionNorm]:
    """Parse un fichier reunionCommission_type."""
    reunion = data.get("reunion") or data
    uid = _safe_str(reunion.get("uid"))
    if not uid:
        return None

    cycle = reunion.get("cycleDeVie") or {}
    date_str = cycle.get("dateDebut") or reunion.get("dateDebut") or reunion.get("date")
    d = _parse_date(date_str)
    if not d:
        return None

    is_senat = _is_senat(reunion)

    # Heures
    heure_debut = _safe_str(cycle.get("heureDebut") or reunion.get("heureDebut"))
    heure_fin = _safe_str(cycle.get("heureFin") or reunion.get("heureFin"))

    # Titre
    titre = _safe_str(
        reunion.get("libelle") or reunion.get("libelleAbrev") or reunion.get("intitule")
    )

    # Organe (commission)
    organe_ref = reunion.get("organeRef") or reunion.get("organeReunionRef")
    if isinstance(organe_ref, dict):
        organe_ref = organe_ref.get("#text")
    organe_id = _safe_str(organe_ref)
    organe_libelle = _safe_str(
        reunion.get("libelleOrgane") or reunion.get("organeLibelle")
    )

    # Participants (présences)
    participants_raw = reunion.get("participants") or reunion.get("presences") or {}
    if isinstance(participants_raw, dict):
        participants_list = (
            participants_raw.get("participant")
            or participants_raw.get("presence")
            or []
        )
    else:
        participants_list = participants_raw

    if not isinstance(participants_list, list):
        participants_list = [participants_list] if participants_list else []

    depute_ids = _extract_depute_ids(participants_list)

    return ReunionCommissionNorm(
        id=uid,
        date=d,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        titre=titre,
        organe_id=organe_id,
        organe_libelle=organe_libelle,
        is_senat=is_senat,
        legislature=LEGISLATURE,
        depute_ids=depute_ids,
    )


def parse_file(
    filename: str, content: bytes
) -> tuple[Optional[SeanceNorm], Optional[ReunionCommissionNorm]]:
    """Détermine le type et parse le fichier JSON correspondant."""
    try:
        data = json.loads(content)
    except Exception:
        return None, None

    # Discriminer le type
    reunion = data.get("reunion") or data
    xsi_type = reunion.get("xsi:type", "")

    # Les réunions de commission ont souvent "reunionCommission_type" ou un UID Cxxx
    uid = reunion.get("uid", "")
    is_commission = (
        "reunionCommission" in xsi_type
        or (isinstance(uid, str) and "RC" in uid)
        or "commission" in xsi_type.lower()
    )

    # Certains fichiers sont des séances ordinaires
    is_seance = (
        "seance" in xsi_type.lower()
        or (isinstance(uid, str) and uid.startswith("RUANR5L17S"))
        or (isinstance(uid, str) and uid.startswith("RUSN"))
    )

    if is_commission and not is_seance:
        return None, parse_reunion_commission(data)
    elif is_seance or not is_commission:
        # Par défaut, traiter comme séance
        seance = parse_seance(data)
        if seance:
            return seance, None
        # Fallback commission
        return None, parse_reunion_commission(data)

    return None, None


# ---------------------------------------------------------------------------
# DB upserts
# ---------------------------------------------------------------------------


async def upsert_seances(
    conn: psycopg.AsyncConnection,
    seances: list[SeanceNorm],
) -> None:
    if not seances:
        return
    for s in seances:
        await conn.execute(
            """
            INSERT INTO seances
                (id, date, titre, type_seance, is_senat, legislature, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET
                date = EXCLUDED.date,
                titre = EXCLUDED.titre,
                type_seance = EXCLUDED.type_seance,
                is_senat = EXCLUDED.is_senat,
                updated_at = now()
            """,
            (s.id, s.date, s.titre, s.type_seance, s.is_senat, s.legislature),
        )
        # Points ODJ : supprimer + réinsérer
        await conn.execute("DELETE FROM points_odj WHERE seance_id = %s", (s.id,))
        for i, titre in enumerate(s.points_odj):
            await conn.execute(
                "INSERT INTO points_odj (seance_id, ordre, titre) VALUES (%s, %s, %s)",
                (s.id, i + 1, titre),
            )


async def upsert_reunions(
    conn: psycopg.AsyncConnection,
    reunions: list[ReunionCommissionNorm],
    known_depute_ids: set[str],
    known_organe_ids: set[str],
) -> None:
    if not reunions:
        return
    for r in reunions:
        # Vérifier que l'organe existe avant d'insérer la FK
        organe_id = r.organe_id if r.organe_id in known_organe_ids else None
        await conn.execute(
            """
            INSERT INTO reunions_commission
                (id, date, heure_debut, heure_fin, titre, organe_id, organe_libelle,
                 is_senat, legislature, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE SET
                date = EXCLUDED.date,
                heure_debut = EXCLUDED.heure_debut,
                heure_fin = EXCLUDED.heure_fin,
                titre = EXCLUDED.titre,
                organe_id = EXCLUDED.organe_id,
                organe_libelle = EXCLUDED.organe_libelle,
                is_senat = EXCLUDED.is_senat,
                updated_at = now()
            """,
            (
                r.id,
                r.date,
                r.heure_debut,
                r.heure_fin,
                r.titre,
                organe_id,
                r.organe_libelle,
                r.is_senat,
                r.legislature,
            ),
        )
        # Présences : supprimer + réinsérer (uniquement députés connus)
        await conn.execute(
            "DELETE FROM presences_commission WHERE reunion_id = %s", (r.id,)
        )
        for dep_id in r.depute_ids:
            if dep_id in known_depute_ids:
                await conn.execute(
                    "INSERT INTO presences_commission (reunion_id, depute_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (r.id, dep_id),
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run() -> None:
    database_url = os.environ["DATABASE_URL"]
    # Convertir URL asyncpg → psycopg
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    logger.info("Téléchargement de l'agenda…")
    zip_bytes = await _download_zip(ZIP_URL)
    logger.info("ZIP téléchargé (%d Mo)", len(zip_bytes) // 1_048_576)

    seances: list[SeanceNorm] = []
    reunions: list[ReunionCommissionNorm] = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("%d fichiers JSON dans l'archive", len(json_files))
        for name in json_files:
            with zf.open(name) as f:
                content = f.read()
            seance, reunion = parse_file(name, content)
            if seance:
                seances.append(seance)
            elif reunion:
                reunions.append(reunion)

    logger.info(
        "Parsed: %d séances, %d réunions commission", len(seances), len(reunions)
    )

    async with await psycopg.AsyncConnection.connect(db_url, autocommit=False) as conn:
        # Charger IDs connus pour éviter FK violations
        depute_ids = {
            row[0] async for row in await conn.execute("SELECT id FROM deputes")
        }
        organe_ids = {
            row[0] async for row in await conn.execute("SELECT id FROM organes")
        }

        async with conn.transaction():
            await upsert_seances(conn, seances)
            logger.info("Séances insérées/mises à jour : %d", len(seances))

        async with conn.transaction():
            await upsert_reunions(conn, reunions, depute_ids, organe_ids)
            logger.info("Réunions commission insérées/mises à jour : %d", len(reunions))

    logger.info("Ingestion agenda terminée.")


def handle(event, context):
    """Entrypoint Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
    return {"statusCode": 200, "body": "OK"}


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
