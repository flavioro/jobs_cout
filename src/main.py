from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes_jobs import router as jobs_router
from src.core.config import get_settings
from src.core.logging_config import configure_logging
from src.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    yield


app = FastAPI(
    title="JobScout v2",
    version="2.0.0",
    description="Pipeline de ingestão de vagas do LinkedIn por URL direta, com related jobs globais e promoção em lote.",
    lifespan=lifespan,
)

app.include_router(jobs_router)
