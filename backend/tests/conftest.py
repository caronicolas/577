import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.main import app
from db.session import get_session

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/les577_test",
)

# NullPool : pas de pool persistant, évite les conflits d'event loop avec asyncpg
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
AsyncTestSession = async_sessionmaker(engine_test, expire_on_commit=False)

_thread_pool = ThreadPoolExecutor(max_workers=1)


def _run_alembic_upgrade(url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def setup_db():
    """Applique les migrations Alembic avant chaque test et détruit le schéma après.

    _run_alembic_upgrade est exécuté dans un thread dédié pour éviter le conflit
    entre asyncio.run() (appelé dans env.py) et la boucle pytest-asyncio déjà active.
    Le schéma public est recréé from scratch pour garantir une base propre à chaque
    test.
    """
    loop = asyncio.get_running_loop()
    async with engine_test.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await loop.run_in_executor(_thread_pool, _run_alembic_upgrade, TEST_DATABASE_URL)
    yield
    async with engine_test.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture
async def session() -> AsyncSession:
    async with AsyncTestSession() as s:
        yield s


@pytest.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()
