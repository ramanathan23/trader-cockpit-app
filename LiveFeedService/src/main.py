import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .infrastructure.redis.publisher import SignalPublisher
from .repositories.candle_repository import CandleRepository
from .repositories.symbol_repository import SymbolRepository
from .services.feed_service import FeedService
from .api.routes import router

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_POOL_CONNECT_TIMEOUT = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── DB pool ───────────────────────────────────────────────────────────────
    try:
        pool = await asyncio.wait_for(
            create_pool(
                settings.database_url,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                command_timeout=settings.db_command_timeout,
            ),
            timeout=_POOL_CONNECT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.critical(
            "Could not connect to the database within %ds. "
            "Is TimescaleDB running?",
            _POOL_CONNECT_TIMEOUT,
        )
        raise

    await run_migrations(pool, timeout=settings.db_migration_timeout)

    # ── Redis publisher ───────────────────────────────────────────────────────
    publisher = SignalPublisher(settings.redis_url)
    await publisher.connect()

    # ── Repositories ─────────────────────────────────────────────────────────
    symbol_repo = SymbolRepository(pool)
    candle_repo = CandleRepository(pool)

    # ── Feed service (starts WebSocket connections + signal engine) ───────────
    feed_service = FeedService(
        symbol_repo = symbol_repo,
        candle_repo = candle_repo,
        publisher   = publisher,
        settings    = settings,
    )

    app.state.pool         = pool
    app.state.publisher    = publisher
    app.state.feed_service = feed_service

    feed_task = asyncio.create_task(feed_service.run(), name="feed-service")
    logger.info("LiveFeedService ready")

    yield

    feed_task.cancel()
    try:
        await feed_task
    except asyncio.CancelledError:
        pass

    await publisher.close()
    await pool.close()
    logger.info("LiveFeedService shut down")


app = FastAPI(
    title="LiveFeedService",
    description="Real-time tick aggregation, signal detection, and SSE alerts for NSE instruments",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
