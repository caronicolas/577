from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Amendement, Depute, Organe

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
    )
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


@pytest.fixture
async def amendement(session: AsyncSession, depute: Depute) -> Amendement:
    a = Amendement(
        id="AM1",
        numero="42",
        titre="Amendement sur le budget",
        texte_legislature="PLFSS2025",
        date_depot=date(2024, 10, 1),
        sort="Adopté",
        url_an="https://assemblee-nationale.fr/am/42",
        depute_id=depute.id,
        legislature=17,
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


@pytest.fixture
async def amendement2(session: AsyncSession, depute: Depute) -> Amendement:
    a = Amendement(
        id="AM2",
        numero="43",
        titre="Amendement sur la fiscalité",
        texte_legislature="PLF2025",
        date_depot=date(2024, 11, 5),
        sort="Rejeté",
        depute_id=depute.id,
        legislature=17,
    )
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


# ---------------------------------------------------------------------------
# GET /amendements — liste
# ---------------------------------------------------------------------------


async def test_list_amendements_vide(client: AsyncClient):
    r = await client.get("/amendements")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_amendements_retourne_amendement(
    client: AsyncClient, amendement: Amendement
):
    r = await client.get("/amendements")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "AM1"
    assert item["numero"] == "42"
    assert item["titre"] == "Amendement sur le budget"
    assert item["sort"] == "Adopté"
    assert item["depute_id"] == "PA1"


async def test_list_amendements_ordre_date_desc(
    client: AsyncClient, amendement: Amendement, amendement2: Amendement
):
    """Triés par date_depot décroissante."""
    r = await client.get("/amendements")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert items[0]["id"] == "AM2"  # 2024-11-05
    assert items[1]["id"] == "AM1"  # 2024-10-01


async def test_list_amendements_filtre_depute_id(
    client: AsyncClient, amendement: Amendement
):
    r = await client.get("/amendements?depute_id=PA1")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/amendements?depute_id=PA999")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_amendements_filtre_texte(
    client: AsyncClient, amendement: Amendement, amendement2: Amendement
):
    """Filtre exact sur texte_legislature."""
    r = await client.get("/amendements?texte=PLFSS2025")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "AM1"

    r = await client.get("/amendements?texte=PLF2025")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == "AM2"


async def test_list_amendements_filtre_sort(
    client: AsyncClient, amendement: Amendement, amendement2: Amendement
):
    r = await client.get("/amendements?sort=Adopté")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "AM1"

    r = await client.get("/amendements?sort=Rejeté")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == "AM2"


async def test_list_amendements_filtre_sort_partiel(
    client: AsyncClient, amendement: Amendement, amendement2: Amendement
):
    """Le filtre sort est ilike → correspondance partielle."""
    r = await client.get("/amendements?sort=opt")  # "Adopté" contient "opt"
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_list_amendements_pagination(
    client: AsyncClient, amendement: Amendement, amendement2: Amendement
):
    r = await client.get("/amendements?limit=1&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "AM2"

    r = await client.get("/amendements?limit=1&offset=1")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == "AM1"


# ---------------------------------------------------------------------------
# GET /amendements/{id}
# ---------------------------------------------------------------------------


async def test_get_amendement(client: AsyncClient, amendement: Amendement):
    r = await client.get("/amendements/AM1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "AM1"
    assert body["numero"] == "42"
    assert body["titre"] == "Amendement sur le budget"
    assert body["sort"] == "Adopté"
    assert body["legislature"] == 17
    assert body["url_an"] == "https://assemblee-nationale.fr/am/42"


async def test_get_amendement_inclut_depute_et_groupe(
    client: AsyncClient, amendement: Amendement
):
    r = await client.get("/amendements/AM1")
    assert r.status_code == 200
    depute = r.json()["depute"]
    assert depute is not None
    assert depute["id"] == "PA1"
    assert depute["nom"] == "Dupont"
    assert depute["groupe_sigle"] == "RN"
    assert depute["groupe_couleur"] == "#0D378A"


async def test_get_amendement_sans_depute(client: AsyncClient, session: AsyncSession):
    """Un amendement sans député rattaché retourne depute=None."""
    a = Amendement(
        id="AM_ORPHELIN",
        numero="99",
        legislature=17,
        depute_id=None,
    )
    session.add(a)
    await session.commit()

    r = await client.get("/amendements/AM_ORPHELIN")
    assert r.status_code == 200
    assert r.json()["depute"] is None


async def test_get_amendement_inconnu(client: AsyncClient):
    r = await client.get("/amendements/INCONNU")
    assert r.status_code == 404
