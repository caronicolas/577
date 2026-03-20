from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import amendements, deputes, votes
from db.models import Base
from db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Données Assemblée Nationale",
    description="API publique — données open data AN 17e législature",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(deputes.router, prefix="/deputes", tags=["deputes"])
app.include_router(votes.router, prefix="/votes", tags=["votes"])
app.include_router(amendements.router, prefix="/amendements", tags=["amendements"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
