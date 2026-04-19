"""DB pool factory."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


async def create_pool(
    dsn: str,
    *,
    min_size: int = 5,
    max_size: int = 20,
    command_timeout: int = 60,
) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
        max_inactive_connection_lifetime=300,
        server_settings={
            "tcp_keepalives_idle":     "60",
            "tcp_keepalives_interval": "5",
            "tcp_keepalives_count":    "3",
            "lock_timeout":            "30000",
            "idle_in_transaction_session_timeout": "120000",
        },
    )
    logger.info("DB pool created (min=%d, max=%d)", min_size, max_size)
    return pool
