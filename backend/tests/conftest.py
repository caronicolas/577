import os

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.main import app
from db.models import Base
from db.session import get_session

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/les577_test",
)

# NullPool : pas de pool persistant, évite les conflits d'event loop avec asyncpg
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
AsyncTestSession = async_sessionmaker(engine_test, expire_on_commit=False)


def _run_alembic_upgrade(url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def setup_db():
    """Applique les migrations Alembic avant chaque test et détruit le schéma après."""
    _run_alembic_upgrade(TEST_DATABASE_URL)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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
