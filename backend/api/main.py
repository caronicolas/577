from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.routers import agenda, amendements, deputes, groupes, votes
from db.models import Base
from db.session import engine

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://les577.fr", "https://www.les577.fr"],
    allow_origin_regex=r"https://.*\.les577\.fr",
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(deputes.router, prefix="/deputes", tags=["deputes"])
app.include_router(groupes.router, prefix="/groupes", tags=["groupes"])
app.include_router(votes.router, prefix="/votes", tags=["votes"])
app.include_router(amendements.router, prefix="/amendements", tags=["amendements"])
app.include_router(agenda.router, prefix="/agenda", tags=["agenda"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
