from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from shared.config_store import load_overrides, apply_overrides
from .infrastructure.dhan.option_chain_client import OptionChainClient
from .infrastructure.redis.publisher import SignalPublisher
from .infrastructure.redis.token_store import TokenStore
from .repositories.candle_repository import CandleRepository
from .repositories.symbol_repository import SymbolRepository
from .services.feed_service import FeedService
from .services.metrics_service import MetricsService

logger = logging.getLogger(__name__)
_POOL_CONNECT_TIMEOUT = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            "Could not connect to the database within %ds. Is TimescaleDB running?",
            _POOL_CONNECT_TIMEOUT,
        )
        raise

    await run_migrations(pool, timeout=settings.db_migration_timeout)
    apply_overrides(settings, await load_overrides(pool, "livefeed"))

    publisher = SignalPublisher(settings.redis_url, cluster_max=settings.cluster_max_per_candle)
    await publisher.connect()

    token_store = TokenStore(redis_url=settings.redis_url, env_fallback=settings.dhan_access_token)
    await token_store.seed_if_missing()

    symbol_repo     = SymbolRepository(pool)
    candle_repo     = CandleRepository(pool)
    metrics_service = MetricsService(pool)

    feed_service = FeedService(
        symbol_repo=symbol_repo, candle_repo=candle_repo,
        publisher=publisher, token_store=token_store,
        settings=settings, metrics_service=metrics_service,
    )

    app.state.pool                = pool
    app.state.publisher           = publisher
    app.state.token_store         = token_store
    app.state.feed_service        = feed_service
    app.state.metrics             = metrics_service
    app.state.option_chain_client = OptionChainClient(
        client_id=settings.dhan_client_id, token_getter=token_store.get,
    )

    feed_task = asyncio.create_task(feed_service.run(), name="feed-service")
    logger.info("LiveFeedService ready")

    yield

    feed_task.cancel()
    try:
        await feed_task
    except asyncio.CancelledError:
        pass
    await publisher.close()
    await token_store.close()
    await pool.close()
    logger.info("LiveFeedService shut down")
