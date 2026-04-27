"""
Poste les nouveaux scrutins solennels et motions de censure sur Bluesky.
Handler Scaleway : handle(event, context)
CRON recommandé : 10,40 13-21 * * 1-6 (10 min après l'ingestion scrutins)

Variables d'environnement requises :
  DATABASE_URL       — URL PostgreSQL (postgresql+asyncpg://...)
  BSKY_IDENTIFIER    — Handle ou DID du compte (ex : les577.fr)
  BSKY_APP_PASSWORD  — App password Bluesky (pas le mot de passe du compte)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from urllib.parse import unquote

import httpx
import psycopg

logger = logging.getLogger(__name__)

BSKY_PDS = "https://bsky.social/xrpc"
MAX_POST_LENGTH = 300
TYPES_A_POSTER = {"scrutin public solennel", "motion de censure"}


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
# Lecture des scrutins à poster
# ---------------------------------------------------------------------------


async def _get_scrutins_a_poster() -> list[dict]:
    conn_params = _get_conn_params()
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        rows = await conn.execute(
            """
            SELECT id, titre, date_seance, type_vote, sort,
                   nombre_pours, nombre_contres, nombre_abstentions
            FROM scrutins
            WHERE bluesky_posted_at IS NULL
              AND type_vote = ANY(%s)
            ORDER BY date_seance DESC, id DESC
            LIMIT 10
            """,
            (list(TYPES_A_POSTER),),
        )
        scrutins = []
        for row in await rows.fetchall():
            scrutins.append(
                {
                    "id": row[0],
                    "titre": row[1],
                    "date_seance": row[2],
                    "type_vote": row[3],
                    "sort": row[4],
                    "nombre_pours": row[5],
                    "nombre_contres": row[6],
                    "nombre_abstentions": row[7],
                }
            )
    return scrutins


async def _mark_posted(conn: psycopg.AsyncConnection, scrutin_id: str) -> None:
    await conn.execute(
        "UPDATE scrutins SET bluesky_posted_at = %s WHERE id = %s",
        (datetime.now(timezone.utc), scrutin_id),
    )


# ---------------------------------------------------------------------------
# Formatage
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _formate_post(s: dict) -> str:
    sort = s["sort"] or ""
    if sort == "adopté":
        emoji = "✅"
    elif sort == "rejeté":
        emoji = "❌"
    else:
        emoji = "🗳️"

    url_path = f"les577.fr/votes/{s['id']}"
    footer = f"👉 {url_path}"

    stats_parts = []
    if s["nombre_pours"] is not None:
        stats_parts.append(f"Pour : {s['nombre_pours']}")
    if s["nombre_contres"] is not None:
        stats_parts.append(f"Contre : {s['nombre_contres']}")
    if s["nombre_abstentions"] is not None:
        stats_parts.append(f"Abstentions : {s['nombre_abstentions']}")
    stats_line = " · ".join(stats_parts)

    if sort:
        header_prefix = f"{emoji} {sort.capitalize()} — "
    else:
        header_prefix = f"{emoji} "

    # Calcul de l'espace disponible pour le titre
    # Structure : "{header_prefix}{titre}\n\n{stats_line}\n\n{footer}"
    overhead = len(header_prefix) + 4 + len(stats_line) + len(footer)
    available = MAX_POST_LENGTH - overhead

    titre = s["titre"] or ""
    if available > 10:
        titre = _truncate(titre, available)
    else:
        titre = ""

    body = f"{header_prefix}{titre}"
    if stats_line:
        body += f"\n\n{stats_line}"
    body += f"\n\n{footer}"

    return body


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


def _build_facets(text: str, url_path: str) -> list[dict]:
    text_bytes = text.encode("utf-8")
    start = text_bytes.find(url_path.encode("utf-8"))
    if start < 0:
        return []
    return [
        {
            "$type": "app.bsky.richtext.facet",
            "index": {
                "byteStart": start,
                "byteEnd": start + len(url_path.encode("utf-8")),
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": f"https://{url_path}",
                }
            ],
        }
    ]


async def _create_record(
    client: httpx.AsyncClient,
    session: dict,
    text: str,
    url_path: str,
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
    facets = _build_facets(text, url_path)
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
    scrutins = await _get_scrutins_a_poster()

    if not scrutins:
        logger.info("Aucun scrutin solennel à poster.")
        return {"status": "skipped", "reason": "no_scrutins"}

    logger.info("%d scrutin(s) à poster", len(scrutins))

    posted = 0
    errors = 0
    conn_params = _get_conn_params()

    try:
        async with httpx.AsyncClient() as client:
            session = await _create_session(client)
            logger.info("Session Bluesky créée pour %s", session.get("handle"))

            async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
                for s in scrutins:
                    text = _formate_post(s)
                    url_path = f"les577.fr/votes/{s['id']}"
                    logger.info(
                        "Post scrutin %s (%d chars) : %s",
                        s["id"],
                        len(text),
                        text[:80].replace("\n", " "),
                    )
                    try:
                        result = await _create_record(client, session, text, url_path)
                        logger.info("Publié : %s", result.get("uri"))
                        await _mark_posted(conn, s["id"])
                        await conn.commit()
                        posted += 1
                    except httpx.HTTPStatusError as e:
                        logger.error(
                            "Erreur Bluesky pour %s : %s — %s",
                            s["id"],
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
