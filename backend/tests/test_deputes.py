import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Depute, Organe


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
        num_departement="75",
        nom_circonscription="Paris-1",
        place_hemicycle=1,
    )
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


@pytest.fixture
async def depute_sans_mandat_fin(session: AsyncSession, depute: Depute) -> Depute:
    """Le député est en exercice (mandat_fin IS NULL)."""
    return depute


# ---------------------------------------------------------------------------
# GET /deputes
# ---------------------------------------------------------------------------


async def test_list_deputes_vide(client: AsyncClient):
    """Sans données, retourne une liste vide."""
    r = await client.get("/deputes")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_deputes_retourne_depute_en_exercice(
    client: AsyncClient, depute_sans_mandat_fin: Depute
):
    """Un député sans mandat_fin apparaît dans la liste."""
    r = await client.get("/deputes")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "PA1"
    assert item["prenom"] == "Jean"
    assert item["nom"] == "Dupont"
    assert item["groupe"]["sigle"] == "RN"
    assert item["num_departement"] == "75"


async def test_list_deputes_filtre_groupe(
    client: AsyncClient, depute_sans_mandat_fin: Depute
):
    """Filtre ?groupe= retourne uniquement les députés du groupe."""
    r = await client.get("/deputes?groupe=RN")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/deputes?groupe=LFI")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_deputes_filtre_departement(
    client: AsyncClient, depute_sans_mandat_fin: Depute
):
    r = await client.get("/deputes?departement=75")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/deputes?departement=69")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_deputes_recherche_nom(
    client: AsyncClient, depute_sans_mandat_fin: Depute
):
    r = await client.get("/deputes?q=Dupont")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/deputes?q=Martin")
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_deputes_exclut_ancien_depute(
    client: AsyncClient, session: AsyncSession, groupe: Organe
):
    """Un député avec mandat_fin renseigné n'apparaît pas dans la liste."""
    from datetime import date

    ancien = Depute(
        id="PA2",
        nom="Ancien",
        prenom="Paul",
        nom_de_famille="Ancien",
        legislature=17,
        groupe_id=groupe.id,
        mandat_fin=date(2024, 1, 1),
        actif=False,
    )
    session.add(ancien)
    await session.commit()

    r = await client.get("/deputes")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()["items"]]
    assert "PA2" not in ids


# ---------------------------------------------------------------------------
# GET /deputes/{id}
# ---------------------------------------------------------------------------


async def test_get_depute(client: AsyncClient, depute_sans_mandat_fin: Depute):
    r = await client.get("/deputes/PA1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "PA1"
    assert body["nom_de_famille"] == "Dupont"
    assert body["groupe"]["sigle"] == "RN"
    assert body["votes"] == []
    assert body["amendements"] == []


async def test_get_depute_inconnu(client: AsyncClient):
    r = await client.get("/deputes/INCONNU")
    assert r.status_code == 404
