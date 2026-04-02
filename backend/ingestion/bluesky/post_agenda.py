"""
Poste l'agenda du jour sur Bluesky (AT Protocol).
Handler Scaleway : handle(event, context)

Variables d'environnement requises :
  DATABASE_URL       — URL PostgreSQL (postgresql+asyncpg://...)
  BSKY_IDENTIFIER    — Handle ou DID du compte (ex : les577.fr)
  BSKY_APP_PASSWORD  — App password Bluesky (pas le mot de passe du compte)
"""

import asyncio
import logging
import os
from datetime import date, datetime, timezone
from urllib.parse import unquote

import httpx
import psycopg

logger = logging.getLogger(__name__)

BSKY_PDS = "https://bsky.social/xrpc"
MAX_POST_LENGTH = 300


# ---------------------------------------------------------------------------
# Connexion DB (même pattern que scrutins.py)
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
# Lecture des séances du jour
# ---------------------------------------------------------------------------


async def _get_seances_du_jour(today: date) -> list[str]:
    """Retourne les titres des points ODJ des séances plénières AN du jour."""
    conn_params = _get_conn_params()
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        rows = await conn.execute(
            """
            SELECT p.titre
            FROM points_odj p
            JOIN seances s ON s.id = p.seance_id
            WHERE s.date = %s
              AND s.is_senat = false
              AND p.titre IS NOT NULL
            ORDER BY s.id, p.ordre
            """,
            (today,),
        )
        titres = [row[0] for row in await rows.fetchall()]
    return titres


# ---------------------------------------------------------------------------
# Formatage du post
# ---------------------------------------------------------------------------


def _formate_post(today: date, titres: list[str]) -> str:
    mois = [
        "",
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    date_str = f"{today.day} {mois[today.month]} {today.year}"
    header = f"📅 Assemblée Nationale — {date_str}\n\nEn séance aujourd'hui :\n"
    footer = "\n\n👉 les577.fr/agenda"
    budget = MAX_POST_LENGTH - len(header) - len(footer)

    lignes: list[str] = []
    for titre in titres:
        # Tronquer les titres trop longs
        ligne = f"• {titre}"
        if len(ligne) > 80:
            ligne = ligne[:77] + "…"
        if budget - len("\n".join(lignes + [ligne])) < 0:
            break
        lignes.append(ligne)

    return header + "\n".join(lignes) + footer


# ---------------------------------------------------------------------------
# Bluesky AT Protocol
# ---------------------------------------------------------------------------


async def _create_session(client: httpx.AsyncClient) -> dict:
    identifier = os.environ["BSKY_IDENTIFIER"]
    app_password = os.environ["BSKY_APP_PASSWORD"]
    r = await client.post(
        f"{BSKY_PDS}/com.atproto.server.createSession",
        json={"identifier": identifier, "password": app_password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


async def _post_bluesky(client: httpx.AsyncClient, session: dict, text: str) -> dict:
    repo = session["did"]
    token = session["accessJwt"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    r = await client.post(
        f"{BSKY_PDS}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "repo": repo,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": now,
            },
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def _main() -> dict:
    today = date.today()
    logger.info("Vérification agenda du %s", today)

    titres = await _get_seances_du_jour(today)
    if not titres:
        logger.info("Aucune séance AN aujourd'hui — pas de post Bluesky.")
        return {"status": "skipped", "reason": "no_seances"}

    logger.info("%d séance(s) trouvée(s)", len(titres))
    text = _formate_post(today, titres)
    logger.info("Post formaté (%d car.) :\n%s", len(text), text)

    async with httpx.AsyncClient() as client:
        session = await _create_session(client)
        logger.info("Session Bluesky créée pour %s", session.get("handle"))
        result = await _post_bluesky(client, session, text)
        logger.info("Post publié : %s", result.get("uri"))

    return {"status": "ok", "uri": result.get("uri"), "seances": len(titres)}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())
