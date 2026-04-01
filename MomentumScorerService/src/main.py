import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .api.routes import router

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(settings.database_url)
    await run_migrations(pool)
    app.state.pool = pool
    logger.info("MomentumScorerService ready")
    yield
    await pool.close()
    logger.info("MomentumScorerService shut down")


app = FastAPI(
    title="MomentumScorerService",
    description="Computes composite momentum scores for NSE symbols using RSI, MACD, ROC and Volume signals",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
