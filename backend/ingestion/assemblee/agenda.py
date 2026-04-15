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
        # Champ réel : "objet" dans les pointODJ
        titre = _safe_str(
            point.get("objet") or point.get("libelle") or point.get("resumeODJ")
        )
        if titre:
            titres.append(titre)
    return titres


def _extract_depute_ids_from_participants(participants: dict) -> list[str]:
    """Extrait les IDs PA* depuis participantsInternes.participantInterne."""
    if not isinstance(participants, dict):
        return []
    internes = participants.get("participantsInternes") or {}
    if not isinstance(internes, dict):
        return []
    # participantInterne peut être un dict (un seul) ou une liste
    raw = internes.get("participantInterne") or []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    ids = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        ref = _safe_str(p.get("acteurRef"))
        if ref and ref.startswith("PA"):
            ids.append(ref)
    return ids


def _is_senat(reunion_data: dict) -> bool:
    """Détermine si c'est une réunion du Sénat (UID RUSN* ou organe Sénat)."""
    uid = reunion_data.get("uid", "")
    if isinstance(uid, str) and uid.startswith("RUSN"):
        return True
    organe_ref = _safe_str(reunion_data.get("organeReuniRef"))
    if organe_ref and SENAT_ORGANE_REF in organe_ref:
        return True
    return False


def _parse_timestamp(ts) -> Optional[date]:
    """Parse timeStampDebut (ISO datetime) → date."""
    if not ts:
        return None
    return _parse_date(str(ts)[:10])


def _extract_heure(ts) -> Optional[str]:
    """Extrait HH:MM depuis un timeStamp ISO."""
    if not ts:
        return None
    s = str(ts)
    # Format : 2024-10-16T17:00:00.000+02:00
    if "T" in s:
        time_part = s.split("T")[1][:5]  # HH:MM
        return time_part
    return None


def parse_seance(data: dict) -> Optional[SeanceNorm]:
    """Parse un fichier séance_type (UID *IDS*)."""
    reunion = data.get("reunion") or data
    uid = _safe_str(reunion.get("uid"))
    if not uid:
        return None

    ts = reunion.get("timeStampDebut")
    d = _parse_timestamp(ts)
    if not d:
        return None

    is_senat = _is_senat(reunion)
    xsi_type = _safe_str(reunion.get("@xsi:type"))

    # Points ODJ : ODJ.pointsODJ.pointODJ (dict ou liste)
    odj = reunion.get("ODJ") or {}
    points_odj_raw = (odj.get("pointsODJ") or {}).get("pointODJ")
    if points_odj_raw is None:
        points_list: list = []
    elif isinstance(points_odj_raw, dict):
        points_list = [points_odj_raw]
    else:
        points_list = points_odj_raw if isinstance(points_odj_raw, list) else []
    points = _extract_points_odj(points_list)

    return SeanceNorm(
        id=uid,
        date=d,
        titre=None,  # pas de titre global sur les séances
        type_seance=xsi_type,
        is_senat=is_senat,
        legislature=LEGISLATURE,
        points_odj=points,
    )


def parse_reunion_commission(data: dict) -> Optional[ReunionCommissionNorm]:
    """Parse un fichier reunionCommission_type (UID *IDC*)."""
    reunion = data.get("reunion") or data
    uid = _safe_str(reunion.get("uid"))
    if not uid:
        return None

    ts_debut = reunion.get("timeStampDebut")
    ts_fin = reunion.get("timeStampFin")
    d = _parse_timestamp(ts_debut)
    if not d:
        return None

    is_senat = _is_senat(reunion)

    heure_debut = _extract_heure(ts_debut)
    heure_fin = _extract_heure(ts_fin)

    # Organe de la commission
    organe_id = _safe_str(reunion.get("organeReuniRef"))

    # Points ODJ pour avoir le titre de la réunion
    odj = reunion.get("ODJ") or {}
    resume_odj = odj.get("resumeODJ")
    if isinstance(resume_odj, list):
        # Prendre le premier item non vide, supprimer les préfixes "- "
        titre = None
        for item in resume_odj:
            s = _safe_str(str(item).lstrip("- ").strip("'\""))
            if s:
                titre = s
                break
    elif isinstance(resume_odj, dict):
        first_val = next(iter(resume_odj.values()), None)
        titre = _safe_str(resume_odj.get("#text") or first_val)
    else:
        titre = _safe_str(resume_odj)

    # Participants internes (députés)
    participants = reunion.get("participants") or {}
    depute_ids = _extract_depute_ids_from_participants(participants)

    return ReunionCommissionNorm(
        id=uid,
        date=d,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        titre=titre,
        organe_id=organe_id,
        organe_libelle=None,  # résolu lors de l'upsert depuis le dict organes
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

    reunion = data.get("reunion") or data
    xsi_type = _safe_str(reunion.get("@xsi:type")) or ""

    if xsi_type == "seance_type":
        return parse_seance(data), None
    elif xsi_type == "reunionCommission_type":
        return None, parse_reunion_commission(data)

    # Fallback par UID : IDS = séance, IDC = commission
    uid = _safe_str(reunion.get("uid")) or ""
    if "IDS" in uid:
        return parse_seance(data), None
    if "IDC" in uid:
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
    organes: dict[str, str],  # id -> libelle
) -> None:
    if not reunions:
        return
    for r in reunions:
        organe_id = r.organe_id if r.organe_id in organes else None
        organe_libelle = organes.get(r.organe_id) if r.organe_id else None
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
                organe_libelle,
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

    conn_kwargs = dict(
        autocommit=True,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )

    # Charger IDs connus pour éviter FK violations
    async with await psycopg.AsyncConnection.connect(db_url, **conn_kwargs) as conn:
        depute_ids = {
            row[0] async for row in await conn.execute("SELECT id FROM deputes")
        }
        organes = {
            row[0]: row[1]
            async for row in await conn.execute("SELECT id, libelle FROM organes")
        }

        async with conn.transaction():
            await upsert_seances(conn, seances)
            logger.info("Séances insérées/mises à jour : %d", len(seances))

    # Insérer les réunions en rouvrant la connexion toutes les 1000 réunions
    # pour éviter les déconnexions serveur sur les longues sessions (~20 min)
    BATCH = 200
    RECONNECT_EVERY = 1000
    for chunk_start in range(0, len(reunions), RECONNECT_EVERY):
        chunk = reunions[chunk_start : chunk_start + RECONNECT_EVERY]
        async with await psycopg.AsyncConnection.connect(db_url, **conn_kwargs) as conn:
            for i in range(0, len(chunk), BATCH):
                batch = chunk[i : i + BATCH]
                async with conn.transaction():
                    await upsert_reunions(conn, batch, depute_ids, organes)
                logger.info(
                    "Réunions insérées : %d/%d",
                    min(chunk_start + i + BATCH, len(reunions)),
                    len(reunions),
                )
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
