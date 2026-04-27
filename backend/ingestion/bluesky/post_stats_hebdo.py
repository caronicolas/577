"""
Poste les stats de participation aux votes de la semaine précédente sur Bluesky.
Handler Scaleway : handle(event, context)
CRON recommandé : 0 8 * * 1 (lundi 08:00 UTC, après la semaine parlementaire)

Variables d'environnement requises :
  DATABASE_URL       — URL PostgreSQL (postgresql+asyncpg://...)
  BSKY_IDENTIFIER    — Handle ou DID du compte (ex : les577.fr)
  BSKY_APP_PASSWORD  — App password Bluesky (pas le mot de passe du compte)
"""

import asyncio
import logging
import os
from datetime import date, datetime, timedelta, timezone
from urllib.parse import unquote

import httpx
import psycopg

logger = logging.getLogger(__name__)

BSKY_PDS = "https://bsky.social/xrpc"
MAX_POST_LENGTH = 300
URL_PATH = "les577.fr/votes"

MOIS = [
    "",
    "jan.",
    "fév.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sep.",
    "oct.",
    "nov.",
    "déc.",
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
# Calcul des stats
# ---------------------------------------------------------------------------


def _semaine_precedente() -> tuple[date, date]:
    """Retourne (lundi, dimanche) de la semaine précédente."""
    today = date.today()
    lundi_cette_semaine = today - timedelta(days=today.weekday())
    lundi = lundi_cette_semaine - timedelta(weeks=1)
    dimanche = lundi_cette_semaine - timedelta(days=1)
    return lundi, dimanche


async def _get_stats(lundi: date, dimanche: date) -> tuple[int, list[dict]]:
    """Retourne (nb_scrutins, participation_par_groupe)."""
    conn_params = _get_conn_params()
    async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
        # Nombre de scrutins de la semaine
        row = await (
            await conn.execute(
                "SELECT COUNT(*) FROM scrutins"
                " WHERE date_seance >= %s AND date_seance <= %s",
                (lundi, dimanche),
            )
        ).fetchone()
        nb_scrutins = row[0] if row else 0

        if nb_scrutins == 0:
            return 0, []

        # Taux de participation par groupe (groupes avec >= 10 membres actifs)
        rows = await (
            await conn.execute(
                """
                SELECT
                    o.sigle,
                    ROUND(
                        COUNT(DISTINCT CASE WHEN vd.position != 'nonVotant'
                            THEN vd.depute_id END)::numeric
                        / NULLIF(COUNT(DISTINCT vd.depute_id), 0) * 100
                    ) AS taux,
                    COUNT(DISTINCT vd.depute_id) AS nb_membres
                FROM votes_deputes vd
                JOIN deputes d ON d.id = vd.depute_id AND d.actif = true
                JOIN organes o ON o.id = d.groupe_id
                JOIN scrutins s ON s.id = vd.scrutin_id
                WHERE s.date_seance >= %s AND s.date_seance <= %s
                GROUP BY o.id, o.sigle
                HAVING COUNT(DISTINCT vd.depute_id) >= 10
                ORDER BY taux DESC
                """,
                (lundi, dimanche),
            )
        ).fetchall()

    groupes = [
        {"sigle": r[0], "taux": int(r[1]), "nb_membres": int(r[2])} for r in rows
    ]
    return nb_scrutins, groupes


# ---------------------------------------------------------------------------
# Formatage
# ---------------------------------------------------------------------------

MEDAILLES = ["🥇", "🥈", "🥉"]


def _formate_date(d: date) -> str:
    return f"{d.day} {MOIS[d.month]}"


def _formate_post(
    lundi: date, dimanche: date, nb_scrutins: int, groupes: list[dict]
) -> str:
    """
    Exemple :
    📊 Semaine du 21 avr. — 8 votes

    Participation :
    🥇 RN : 91%
    🥈 EPR : 88%
    🥉 SOC : 84%
    ⬇️ LIOT : 58%

    👉 les577.fr/votes
    """
    vote_label = "vote" if nb_scrutins == 1 else "votes"
    header = (
        f"📊 Semaine du {_formate_date(lundi)}"
        f" au {_formate_date(dimanche)} — {nb_scrutins} {vote_label}"
    )
    footer = f"👉 {URL_PATH}"

    lines = ["Participation aux votes :"]
    if len(groupes) >= 2:
        # Top 3 + dernier
        top = groupes[: min(3, len(groupes) - 1)]
        bottom = groupes[-1]
        for i, g in enumerate(top):
            medal = MEDAILLES[i] if i < len(MEDAILLES) else "▪️"
            lines.append(f"{medal} {g['sigle']} : {g['taux']}%")
        if bottom["sigle"] not in {g["sigle"] for g in top}:
            lines.append(f"⬇️ {bottom['sigle']} : {bottom['taux']}%")
    else:
        for g in groupes:
            lines.append(f"▪️ {g['sigle']} : {g['taux']}%")

    body = "\n".join(lines)
    return f"{header}\n\n{body}\n\n{footer}"


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
    text_bytes = text.encode("utf-8")
    start = text_bytes.find(URL_PATH.encode("utf-8"))
    if start < 0:
        return []
    return [
        {
            "$type": "app.bsky.richtext.facet",
            "index": {
                "byteStart": start,
                "byteEnd": start + len(URL_PATH.encode("utf-8")),
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": f"https://{URL_PATH}",
                }
            ],
        }
    ]


async def _create_record(client: httpx.AsyncClient, session: dict, text: str) -> dict:
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
    lundi, dimanche = _semaine_precedente()
    logger.info("Stats semaine du %s au %s", lundi, dimanche)

    nb_scrutins, groupes = await _get_stats(lundi, dimanche)

    if nb_scrutins == 0:
        logger.info("Aucun scrutin la semaine précédente, rien à poster.")
        return {"status": "skipped", "reason": "no_scrutins"}

    text = _formate_post(lundi, dimanche, nb_scrutins, groupes)
    logger.info("Post (%d chars) : %s", len(text), text[:80].replace("\n", " "))

    try:
        async with httpx.AsyncClient() as client:
            session = await _create_session(client)
            logger.info("Session Bluesky créée pour %s", session.get("handle"))
            result = await _create_record(client, session, text)
            logger.info("Publié : %s", result.get("uri"))
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "http_status": e.response.status_code,
            "bsky_error": e.response.text,
        }

    return {"status": "ok", "nb_scrutins": nb_scrutins, "nb_groupes": len(groupes)}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
