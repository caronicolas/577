"""
Poste l'agenda du jour sur Bluesky (AT Protocol) sous forme de thread.
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

MOIS = [
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
# Formatage
# ---------------------------------------------------------------------------


def _formate_post_principal(today: date, nb: int) -> str:
    date_str = f"{today.day} {MOIS[today.month]} {today.year}"
    return (
        f"📅 Assemblée Nationale — {date_str}\n\n"
        f"En séance ({nb} sujet{'s' if nb > 1 else ''}) 👇\n\n"
        f"👉 les577.fr/agenda"
    )


def _formate_reply(i: int, nb: int, titre: str) -> str:
    text = f"{i}/{nb} • {titre}"
    if len(text) > MAX_POST_LENGTH:
        text = text[: MAX_POST_LENGTH - 1] + "…"
    return text


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
    reply_ref: dict | None = None,
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

    if reply_ref:
        record["reply"] = reply_ref

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
    today = datetime.now(timezone.utc).date()
    logger.info("Vérification agenda du %s (UTC)", today)

    titres = await _get_seances_du_jour(today)
    if not titres:
        logger.info("Aucune séance AN aujourd'hui — pas de post Bluesky.")
        return {"status": "skipped", "reason": "no_seances"}

    nb = len(titres)
    logger.info("%d sujet(s) au programme", nb)

    try:
        async with httpx.AsyncClient() as client:
            session = await _create_session(client)
            logger.info("Session Bluesky créée pour %s", session.get("handle"))

            # Post principal
            text_principal = _formate_post_principal(today, nb)
            root = await _create_record(client, session, text_principal)
            logger.info("Post principal publié : %s", root.get("uri"))

            root_ref = {"uri": root["uri"], "cid": root["cid"]}
            parent_ref = root_ref

            # Replies — une par sujet
            for i, titre in enumerate(titres, 1):
                text_reply = _formate_reply(i, nb, titre)
                reply_ref = {"root": root_ref, "parent": parent_ref}
                result = await _create_record(client, session, text_reply, reply_ref)
                logger.info("Reply %d/%d publiée : %s", i, nb, result.get("uri"))
                parent_ref = {"uri": result["uri"], "cid": result["cid"]}

    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "http_status": e.response.status_code,
            "bsky_error": e.response.text,
        }

    return {"status": "ok", "thread_uri": root_ref["uri"], "replies": nb}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
