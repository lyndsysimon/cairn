from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cairn.api.routes import agents, health, providers
from cairn.config import settings
from cairn.db.connection import close_pool, create_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool(settings.database_url)
    yield
    await close_pool()


app = FastAPI(title="Cairn", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(agents.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
