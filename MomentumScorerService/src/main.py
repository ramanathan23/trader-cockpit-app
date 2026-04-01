import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .api.routes import router
from .repositories.score_repository import ScoreRepository
from .services.score_service import ScoreService

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(
        settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=settings.db_command_timeout,
    )
    await run_migrations(pool)
    app.state.pool          = pool
    app.state.score_repo    = ScoreRepository(pool)
    app.state.score_service = ScoreService(pool)
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
