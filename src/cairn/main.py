from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cairn.api.dependencies import get_execution_service
from cairn.api.routes import agents, credentials, health, providers, runs, webhooks
from cairn.config import settings
from cairn.db.connection import close_pool, create_pool
from cairn.scheduling import CronScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(settings.database_url)
    scheduler = CronScheduler(pool=pool, execution_service=get_execution_service())
    await scheduler.start()
    yield
    await scheduler.stop()
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
app.include_router(credentials.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
