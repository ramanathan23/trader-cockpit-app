import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .api.routes import router
from .repositories.price_repository import PriceRepository
from .repositories.symbol_repository import SymbolRepository
from .repositories.sync_state_repository import SyncStateRepository
from .services.sync_service import SyncService

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
    app.state.pool             = pool
    app.state.price_repo       = PriceRepository(pool)
    app.state.symbol_repo      = SymbolRepository(pool)
    app.state.sync_state_repo  = SyncStateRepository(pool)
    app.state.sync_service     = SyncService(pool)
    logger.info("DataSyncService ready")
    yield
    await pool.close()
    logger.info("DataSyncService shut down")


app = FastAPI(
    title="DataSyncService",
    description="Fetches and stores OHLCV data for NSE symbols via yfinance / Dhan → TimescaleDB",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
