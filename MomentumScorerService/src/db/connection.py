import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

_MIGRATION = Path(__file__).parent / "migrations" / "001_schema.sql"


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn,
        min_size=3,
        max_size=10,
        command_timeout=60,
    )
    logger.info("Database pool created")
    return pool


async def run_migrations(pool: asyncpg.Pool) -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Migrations applied")
