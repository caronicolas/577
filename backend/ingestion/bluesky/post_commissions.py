"""
Poste les réunions de commission AN non encore postées dont l'heure de début
est inférieure ou égale à maintenant + 15 min (heure Paris).
Handler Scaleway : handle(event, context)
CRON recommandé : */15 * * * *

Variables d'environnement requises :
  DATABASE_URL       — URL PostgreSQL (postgresql+asyncpg://...)
  BSKY_IDENTIFIER    — Handle ou DID du compte (ex : les577.fr)
  BSKY_APP_PASSWORD  — App password Bluesky (pas le mot de passe du compte)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import httpx
import psycopg

logger = logging.getLogger(__name__)

BSKY_PDS = "https://bsky.social/xrpc"
MAX_POST_LENGTH = 300
WINDOW_MINUTES = 15


# ---------------------------------------------------------------------------
# Connexion DB
# ---------------------------------------------------------------------------


def _get_conn_params() -> dict:
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
# Lecture des réunions à poster
# ---------------------------------------------------------------------------


async def _get_reunions_a_poster(today: str, heure_limite: str) -> list[dict]:
    """
    Retourne les réunions de commission AN non-Sénat non encore postées
    dont heure_debut <= heure_limite (format HH:MM), pour la date donnée.
    """
    conn_params = _get_conn_params()
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        rows = await conn.execute(
            """
            SELECT id, heure_debut, heure_fin, titre, organe_libelle
            FROM reunions_commission
            WHERE date = %s
              AND is_senat = false
              AND bluesky_posted_at IS NULL
              AND heure_debut <= %s
            ORDER BY heure_debut, id
            """,
            (today, heure_limite),
        )
        reunions = []
        for row in await rows.fetchall():
            reunions.append(
                {
                    "id": row[0],
                    "heure_debut": row[1],
                    "heure_fin": row[2],
                    "titre": row[3],
                    "organe_libelle": row[4],
                }
            )
    return reunions


async def _mark_posted(conn: psycopg.AsyncConnection, reunion_id: str) -> None:
    await conn.execute(
        "UPDATE reunions_commission SET bluesky_posted_at = %s WHERE id = %s",
        (datetime.now(timezone.utc), reunion_id),
    )


# ---------------------------------------------------------------------------
# Formatage
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    """Tronque un texte à max_len graphèmes (approx) en ajoutant '…'."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _formate_post_commission(r: dict) -> str:
    """
    Formate le post pour une réunion de commission.
    Exemple :
        🏛️ Commission des lois — 09h00

        Audition de M. Dupont sur le projet de loi XYZ.

        👉 les577.fr/agenda
    """
    heure = r["heure_debut"] or "?"
    # Remplacement ":" → "h" pour un format plus naturel en français
    heure_fmt = heure.replace(":", "h")
    organe = r["organe_libelle"] or "Commission"
    titre = r["titre"] or ""

    header = f"🏛️ {organe} — {heure_fmt}"
    footer = "👉 les577.fr/agenda"

    if titre:
        # Capitalise le premier caractère si nécessaire
        titre = titre[0].upper() + titre[1:] if titre else titre
        body = f"\n\n{titre}\n\n"
        full = header + body + footer
        if len(full) > MAX_POST_LENGTH:
            # Calcul de l'espace disponible pour le titre
            overhead = len(header) + len("\n\n") + len("\n\n") + len(footer)
            available = MAX_POST_LENGTH - overhead
            if available > 10:
                titre = _truncate(titre, available)
                full = header + f"\n\n{titre}\n\n" + footer
            else:
                # Pas assez de place pour le titre : on l'omet
                full = _truncate(header + f"\n\n{footer}", MAX_POST_LENGTH)
    else:
        full = header + f"\n\n{footer}"
        full = _truncate(full, MAX_POST_LENGTH)

    return full


# ---------------------------------------------------------------------------
# Bluesky AT Protocol
# ---------------------------------------------------------------------------


async def _create_session(client: httpx.AsyncClient) -> dict:
    r = await client.post(
        f"{BSKY_PDS}/com.atproto.server.createSession",
        json={
            "identifier": os.environ["BSKY_IDENTIFIER"],
            "password": os.environ["BSKY_APP_PASSWORD"],
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _build_facets(text: str) -> list[dict]:
    """Détecte les liens https:// dans le texte et construit les facets."""
    facets = []
    text_bytes = text.encode("utf-8")
    for link in ["les577.fr/agenda"]:
        uri = f"https://{link}"
        start = text_bytes.find(link.encode("utf-8"))
        if start >= 0:
            facets.append(
                {
                    "$type": "app.bsky.richtext.facet",
                    "index": {
                        "byteStart": start,
                        "byteEnd": start + len(link.encode("utf-8")),
                    },
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}],
                }
            )
    return facets


async def _create_record(
    client: httpx.AsyncClient,
    session: dict,
    text: str,
) -> dict:
    repo = session["did"]
    token = session["accessJwt"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    record: dict = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
        "langs": ["fr"],
    }

    facets = _build_facets(text)
    if facets:
        record["facets"] = facets

    r = await client.post(
        f"{BSKY_PDS}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {token}"},
        json={"repo": repo, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    if not r.is_success:
        logger.error("Bluesky createRecord error %s : %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def _main() -> dict:
    now_utc = datetime.now(timezone.utc)
    # Heure Paris (UTC+2 en été, UTC+1 en hiver)
    # Approximation DST : mois 3 (après le 25) → mois 10 (avant le 25).
    month = now_utc.month
    is_summer = (
        3 < month < 10
        or (month == 3 and now_utc.day >= 25)
        or (month == 10 and now_utc.day < 25)
    )
    paris_offset = timedelta(hours=2 if is_summer else 1)
    now_paris = now_utc + paris_offset

    today = now_paris.strftime("%Y-%m-%d")
    # Limite : maintenant + WINDOW_MINUTES pour annoncer les réunions imminentes
    heure_limite = (now_paris + timedelta(minutes=WINDOW_MINUTES)).strftime("%H:%M")

    logger.info("Heure limite : %s (Paris) pour %s", heure_limite, today)

    reunions = await _get_reunions_a_poster(today, heure_limite)

    if not reunions:
        logger.info("Aucune réunion de commission à poster.")
        return {"status": "skipped", "reason": "no_reunions"}

    logger.info("%d réunion(s) à poster", len(reunions))

    posted = 0
    errors = 0
    conn_params = _get_conn_params()

    try:
        async with httpx.AsyncClient() as client:
            session = await _create_session(client)
            logger.info("Session Bluesky créée pour %s", session.get("handle"))

            async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
                for r in reunions:
                    text = _formate_post_commission(r)
                    logger.info(
                        "Post commission %s (%d graphèmes) : %s",
                        r["id"],
                        len(text),
                        text[:60].replace("\n", " "),
                    )
                    try:
                        result = await _create_record(client, session, text)
                        logger.info("Publié : %s", result.get("uri"))
                        await _mark_posted(conn, r["id"])
                        await conn.commit()
                        posted += 1
                    except httpx.HTTPStatusError as e:
                        logger.error(
                            "Erreur Bluesky pour %s : %s — %s",
                            r["id"],
                            e.response.status_code,
                            e.response.text,
                        )
                        errors += 1

    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "http_status": e.response.status_code,
            "bsky_error": e.response.text,
        }

    return {"status": "ok", "posted": posted, "errors": errors}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
