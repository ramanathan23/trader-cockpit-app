import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .api.routes import router
from .services.indicators_service import IndicatorsService
from .services.setup_behavior_service import SetupBehaviorService

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
    app.state.pool = pool
    app.state.indicators_service = IndicatorsService(pool)
    app.state.setup_behavior_service = SetupBehaviorService(pool)
    logger.info("IndicatorsService ready")
    yield
    await pool.close()
    logger.info("IndicatorsService shut down")


app = FastAPI(
    title="IndicatorsService",
    description="Computes technical indicators and pattern detection for NSE symbols from daily OHLCV",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
