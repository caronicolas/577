"""
Enrichissement des réseaux sociaux des députés depuis NosDéputés.fr.
Handler Scaleway : handle(event, context)

Source : https://www.nosdeputes.fr/deputes/json
Licence : ODbL — "NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale"
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote

import httpx
import psycopg
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

NOSDEPUTES_URL = "https://www.nosdeputes.fr/deputes/json"


# ---------------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------------


@dataclass
class SocialMedia:
    depute_id: str  # ex: PA642847
    twitter: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    bluesky_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Extraction des URLs depuis sites_web
# ---------------------------------------------------------------------------

_FACEBOOK_RE = re.compile(
    r"https?://(?:[\w-]+\.)?facebook\.com/([^/?#\s]+)", re.IGNORECASE
)
_INSTAGRAM_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/([^/?#\s]+)", re.IGNORECASE
)
_BLUESKY_RE = re.compile(
    r"https?://(?:www\.)?bsky\.(?:app|social)/profile/([^/?#\s]+)", re.IGNORECASE
)


def _canonical_facebook(url: str) -> Optional[str]:
    m = _FACEBOOK_RE.search(url)
    if not m:
        return None
    handle = m.group(1).rstrip("/")
    if handle.lower() in ("pages", "groups", "sharer", "share"):
        return None
    return f"https://www.facebook.com/{handle}"


def _canonical_instagram(url: str) -> Optional[str]:
    m = _INSTAGRAM_RE.search(url)
    if not m:
        return None
    handle = m.group(1).rstrip("/").split("?")[0]
    if handle.lower() in ("p", "reel", "stories", "explore"):
        return None
    return f"https://www.instagram.com/{handle}"


def _canonical_bluesky(url: str) -> Optional[str]:
    m = _BLUESKY_RE.search(url)
    if not m:
        return None
    handle = m.group(1).rstrip("/")
    return f"https://bsky.app/profile/{handle}"


def _extract_social(
    sites_web: list[dict],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Retourne (facebook_url, instagram_url, bluesky_url)."""
    facebook = instagram = bluesky = None
    for item in sites_web:
        url = item.get("site", "")
        if not url:
            continue
        if not facebook and "facebook.com" in url:
            facebook = _canonical_facebook(url)
        if not instagram and "instagram.com" in url:
            instagram = _canonical_instagram(url)
        if not bluesky and "bsky." in url:
            bluesky = _canonical_bluesky(url)
    return facebook, instagram, bluesky


# ---------------------------------------------------------------------------
# Fetch NosDéputés
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _fetch_nosdeputes(client: httpx.AsyncClient) -> list[dict]:
    logger.info("Téléchargement NosDéputés : %s", NOSDEPUTES_URL)
    r = await client.get(NOSDEPUTES_URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return r.json()["deputes"]


def _parse_social(deputes_raw: list[dict]) -> list[SocialMedia]:
    results: list[SocialMedia] = []
    for item in deputes_raw:
        d = item.get("depute", {})
        id_an = d.get("id_an")
        if not id_an:
            continue
        depute_id = f"PA{id_an}"
        twitter = d.get("twitter") or None
        sites_web = d.get("sites_web") or []
        facebook, instagram, bluesky = _extract_social(sites_web)
        if twitter or facebook or instagram or bluesky:
            results.append(
                SocialMedia(
                    depute_id=depute_id,
                    twitter=twitter,
                    facebook_url=facebook,
                    instagram_url=instagram,
                    bluesky_url=bluesky,
                )
            )
    logger.info("%d députés avec au moins un réseau social", len(results))
    return results


async def fetch_social_media() -> list[SocialMedia]:
    async with httpx.AsyncClient() as client:
        raw = await _fetch_nosdeputes(client)
    return _parse_social(raw)


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
        hostport, dbname = hostinfo[:slash], hostinfo[slash + 1 :]
    else:
        hostport, dbname = hostinfo, ""
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
# Upsert
# ---------------------------------------------------------------------------

_UPDATE = """
    UPDATE deputes SET
        twitter       = %(twitter)s,
        facebook_url  = %(facebook_url)s,
        instagram_url = %(instagram_url)s,
        bluesky_url   = %(bluesky_url)s,
        updated_at    = now()
    WHERE id = %(depute_id)s
"""


async def upsert_social(records: list[SocialMedia]) -> int:
    updated = 0
    async with await psycopg.AsyncConnection.connect(**_get_conn_params()) as conn:
        for r in records:
            result = await conn.execute(
                _UPDATE,
                {
                    "depute_id": r.depute_id,
                    "twitter": r.twitter,
                    "facebook_url": r.facebook_url,
                    "instagram_url": r.instagram_url,
                    "bluesky_url": r.bluesky_url,
                },
            )
            updated += result.rowcount
        await conn.commit()
    return updated


# ---------------------------------------------------------------------------
# Orchestration + handler Scaleway
# ---------------------------------------------------------------------------


async def _main() -> dict:
    logger.info("Démarrage ingestion réseaux sociaux (NosDéputés)")
    records = await fetch_social_media()
    count = await upsert_social(records)
    logger.info("Terminé : %d députés mis à jour", count)
    return {"status": "ok", "updated": count}


def handle(event: dict, context: object) -> dict:
    """Point d'entrée Scaleway Serverless Functions."""
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
