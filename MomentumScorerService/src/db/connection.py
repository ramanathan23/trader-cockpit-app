import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

_MIGRATION = Path(__file__).parent / "migrations" / "001_schema.sql"


async def create_pool(
    dsn: str,
    *,
    min_size: int = 3,
    max_size: int = 10,
    command_timeout: int = 60,
) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )
    logger.info("Database pool created (min=%d, max=%d)", min_size, max_size)
    return pool


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply schema DDL. All statements use IF NOT EXISTS — safe to re-run."""
    sql = _MIGRATION.read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Migrations applied")
