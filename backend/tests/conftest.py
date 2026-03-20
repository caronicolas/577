import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from db.models import Base
from db.session import get_session

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/an577_test"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncTestSession = async_sessionmaker(engine_test, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
