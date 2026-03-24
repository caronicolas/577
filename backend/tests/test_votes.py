from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Depute, Organe, Scrutin, VoteDepute

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def groupe(session: AsyncSession) -> Organe:
    g = Organe(
        id="PO800520",
        sigle="RN",
        libelle="Rassemblement National",
        couleur="#0D378A",
        legislature=17,
    )
    session.add(g)
    await session.commit()
    await session.refresh(g)
    return g


@pytest.fixture
async def depute(session: AsyncSession, groupe: Organe) -> Depute:
    d = Depute(
        id="PA1",
        nom="Dupont",
        prenom="Jean",
        nom_de_famille="Dupont",
        legislature=17,
        groupe_id=groupe.id,
        place_hemicycle=1,
    )
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


@pytest.fixture
async def scrutin(session: AsyncSession) -> Scrutin:
    s = Scrutin(
        id="VTANR5L17V1",
        numero=1,
        titre="Projet de loi de finances 2025",
        date_seance=date(2024, 11, 15),
        sort="adopté",
        nombre_votants=550,
        nombre_pours=300,
        nombre_contres=200,
        nombre_abstentions=50,
        legislature=17,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest.fixture
async def scrutin2(session: AsyncSession) -> Scrutin:
    s = Scrutin(
        id="VTANR5L17V2",
        numero=2,
        titre="Motion de censure",
        date_seance=date(2024, 12, 1),
        sort="rejeté",
        nombre_votants=570,
        nombre_pours=100,
        nombre_contres=450,
        nombre_abstentions=20,
        legislature=17,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest.fixture
async def vote(session: AsyncSession, scrutin: Scrutin, depute: Depute) -> VoteDepute:
    v = VoteDepute(scrutin_id=scrutin.id, depute_id=depute.id, position="pour")
    session.add(v)
    await session.commit()
    return v


# ---------------------------------------------------------------------------
# GET /votes — liste générale
# ---------------------------------------------------------------------------


async def test_list_votes_vide(client: AsyncClient):
    r = await client.get("/votes")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_votes_retourne_scrutin(client: AsyncClient, scrutin: Scrutin):
    r = await client.get("/votes")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "VTANR5L17V1"
    assert item["numero"] == 1
    assert item["titre"] == "Projet de loi de finances 2025"
    assert item["sort"] == "adopté"
    assert item["nombre_pours"] == 300
    assert item["position"] is None  # pas de filtre depute_id


async def test_list_votes_ordre_chronologique_desc(
    client: AsyncClient, scrutin: Scrutin, scrutin2: Scrutin
):
    """Les scrutins sont triés du plus récent au plus ancien."""
    r = await client.get("/votes")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert items[0]["id"] == "VTANR5L17V2"  # 2024-12-01
    assert items[1]["id"] == "VTANR5L17V1"  # 2024-11-15


async def test_list_votes_recherche_titre(
    client: AsyncClient, scrutin: Scrutin, scrutin2: Scrutin
):
    r = await client.get("/votes?q=finances")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "VTANR5L17V1"


async def test_list_votes_recherche_titre_insensible_casse(
    client: AsyncClient, scrutin: Scrutin
):
    r = await client.get("/votes?q=FINANCES")
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_list_votes_recherche_sans_resultat(
    client: AsyncClient, scrutin: Scrutin
):
    r = await client.get("/votes?q=inexistant")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_votes_pagination(
    client: AsyncClient, scrutin: Scrutin, scrutin2: Scrutin
):
    r = await client.get("/votes?limit=1&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "VTANR5L17V2"

    r = await client.get("/votes?limit=1&offset=1")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == "VTANR5L17V1"


# ---------------------------------------------------------------------------
# GET /votes?depute_id= — filtre par député
# ---------------------------------------------------------------------------


async def test_list_votes_par_depute(client: AsyncClient, vote: VoteDepute):
    """Filtre par député : retourne uniquement ses scrutins avec sa position."""
    r = await client.get("/votes?depute_id=PA1")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "VTANR5L17V1"
    assert item["position"] == "pour"


async def test_list_votes_par_depute_inconnu(client: AsyncClient, scrutin: Scrutin):
    """Un député qui n'a pas voté : liste vide."""
    r = await client.get("/votes?depute_id=INCONNU")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_votes_par_depute_avec_recherche(
    client: AsyncClient, vote: VoteDepute, scrutin2: Scrutin
):
    """Combine depute_id et q : seuls les scrutins du député matchant le titre."""
    r = await client.get("/votes?depute_id=PA1&q=finances")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/votes?depute_id=PA1&q=censure")
    assert r.status_code == 200
    assert r.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /votes/{id}
# ---------------------------------------------------------------------------


async def test_get_scrutin(client: AsyncClient, scrutin: Scrutin):
    r = await client.get("/votes/VTANR5L17V1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "VTANR5L17V1"
    assert body["numero"] == 1
    assert body["titre"] == "Projet de loi de finances 2025"
    assert body["sort"] == "adopté"
    assert body["legislature"] == 17
    assert body["votes"] == []


async def test_get_scrutin_avec_votes(client: AsyncClient, vote: VoteDepute):
    """Le détail d'un scrutin inclut les votes des députés avec groupe."""
    r = await client.get("/votes/VTANR5L17V1")
    assert r.status_code == 200
    body = r.json()
    assert len(body["votes"]) == 1
    v = body["votes"][0]
    assert v["depute_id"] == "PA1"
    assert v["nom"] == "Dupont"
    assert v["position"] == "pour"
    assert v["groupe_sigle"] == "RN"
    assert v["groupe_couleur"] == "#0D378A"
    assert v["place_hemicycle"] == 1


async def test_get_scrutin_inconnu(client: AsyncClient):
    r = await client.get("/votes/INCONNU")
    assert r.status_code == 404
