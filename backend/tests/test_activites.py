from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Amendement, Depute, Scrutin, VoteDepute

# Date dans la 17e législature (>= 2024-06-18)
D_LEG = date(2024, 9, 10)
# Date avant la législature — doit être ignorée
D_AVANT = date(2024, 5, 1)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def depute(session: AsyncSession) -> Depute:
    d = Depute(
        id="PA1",
        nom="Dupont",
        prenom="Jean",
        nom_de_famille="Dupont",
        legislature=17,
    )
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


async def _scrutin(session: AsyncSession, sid: str, d: date) -> Scrutin:
    s = Scrutin(
        id=sid,
        numero=int(sid[-1]),
        titre=f"Scrutin {sid}",
        date_seance=d,
        legislature=17,
    )
    session.add(s)
    await session.commit()
    return s


async def _vote(
    session: AsyncSession, scrutin_id: str, depute_id: str, position: str
) -> VoteDepute:
    v = VoteDepute(scrutin_id=scrutin_id, depute_id=depute_id, position=position)
    session.add(v)
    await session.commit()
    return v


async def _amendement(session: AsyncSession, depute_id: str, d: date) -> Amendement:
    a = Amendement(
        id=f"AM-{d}",
        depute_id=depute_id,
        date_depot=d,
        legislature=17,
    )
    session.add(a)
    await session.commit()
    return a


# ---------------------------------------------------------------------------
# GET /deputes/{id}/activites
# ---------------------------------------------------------------------------


async def test_activites_depute_inconnu(client: AsyncClient):
    r = await client.get("/deputes/INCONNU/activites")
    assert r.status_code == 404


async def test_activites_vide(client: AsyncClient, depute: Depute):
    """Sans vote ni amendement, liste vide."""
    r = await client.get("/deputes/PA1/activites")
    assert r.status_code == 200
    assert r.json() == []


async def test_activite_vote_pour(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Vote 'pour' → present=True, a_vote=True."""
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "pour")

    r = await client.get("/deputes/PA1/activites")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["date"] == str(D_LEG)
    assert items[0]["present"] is True
    assert items[0]["a_vote"] is True
    assert items[0]["a_pris_parole"] is False
    assert items[0]["a_depose_amendement"] is False


async def test_activite_vote_contre(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "contre")

    items = (await client.get("/deputes/PA1/activites")).json()
    assert items[0]["a_vote"] is True
    assert items[0]["present"] is True


async def test_activite_vote_abstention(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "abstention")

    items = (await client.get("/deputes/PA1/activites")).json()
    assert items[0]["a_vote"] is True
    assert items[0]["present"] is True


async def test_activite_non_votant(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """'nonVotant' → present=True mais a_vote=False."""
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "nonVotant")

    items = (await client.get("/deputes/PA1/activites")).json()
    assert len(items) == 1
    assert items[0]["present"] is True
    assert items[0]["a_vote"] is False


async def test_activite_amendement_seul(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Amendement sans vote → present=True, a_vote=False, a_depose_amendement=True."""
    await _amendement(session, "PA1", D_LEG)

    items = (await client.get("/deputes/PA1/activites")).json()
    assert len(items) == 1
    assert items[0]["date"] == str(D_LEG)
    assert items[0]["present"] is True
    assert items[0]["a_vote"] is False
    assert items[0]["a_depose_amendement"] is True


async def test_activite_vote_et_amendement_meme_jour(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Vote + amendement le même jour → une seule entrée avec les deux flags."""
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "pour")
    await _amendement(session, "PA1", D_LEG)

    items = (await client.get("/deputes/PA1/activites")).json()
    assert len(items) == 1
    assert items[0]["a_vote"] is True
    assert items[0]["a_depose_amendement"] is True


async def test_activites_plusieurs_jours_tries(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Plusieurs dates → retournées triées chronologiquement."""
    d1 = date(2024, 9, 10)
    d2 = date(2024, 10, 5)
    d3 = date(2025, 1, 20)
    await _scrutin(session, "VTANR5L17V1", d1)
    await _vote(session, "VTANR5L17V1", "PA1", "pour")
    await _amendement(session, "PA1", d2)
    await _scrutin(session, "VTANR5L17V2", d3)
    await _vote(session, "VTANR5L17V2", "PA1", "contre")

    items = (await client.get("/deputes/PA1/activites")).json()
    assert len(items) == 3
    assert items[0]["date"] == str(d1)
    assert items[1]["date"] == str(d2)
    assert items[2]["date"] == str(d3)


async def test_activites_plusieurs_votes_meme_jour(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Plusieurs scrutins le même jour → une seule entrée agrégée."""
    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _scrutin(session, "VTANR5L17V2", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA1", "pour")
    await _vote(session, "VTANR5L17V2", "PA1", "contre")

    items = (await client.get("/deputes/PA1/activites")).json()
    assert len(items) == 1
    assert items[0]["a_vote"] is True


async def test_activites_ignore_avant_legislature(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Les événements avant le 2024-06-18 sont ignorés."""
    await _scrutin(session, "VTANR5L17V1", D_AVANT)
    await _vote(session, "VTANR5L17V1", "PA1", "pour")
    await _amendement(session, "PA1", D_AVANT)

    r = await client.get("/deputes/PA1/activites")
    assert r.json() == []


async def test_activites_autre_depute_non_inclus(
    client: AsyncClient, session: AsyncSession, depute: Depute
):
    """Les votes d'un autre député ne remontent pas."""
    autre = Depute(
        id="PA2", nom="Martin", prenom="Paul", nom_de_famille="Martin", legislature=17
    )
    session.add(autre)
    await session.commit()

    await _scrutin(session, "VTANR5L17V1", D_LEG)
    await _vote(session, "VTANR5L17V1", "PA2", "pour")

    r = await client.get("/deputes/PA1/activites")
    assert r.json() == []
