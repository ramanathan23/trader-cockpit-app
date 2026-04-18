"""Database connection and migration utilities."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


async def create_pool(
    dsn: str,
    min_size: int = 3,
    max_size: int = 10,
    command_timeout: float = 10.0,
) -> asyncpg.Pool:
    """Create asyncpg connection pool."""
    logger.info(f"Creating DB pool (min={min_size}, max={max_size})")
    pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )
    return pool


async def run_migrations(pool: asyncpg.Pool, timeout: float = 30.0) -> None:
    """Run database schema migrations."""
    logger.info("Running migrations")
    
    async with pool.acquire() as conn:
        # Read schema SQL
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        
        with open(schema_path) as f:
            schema_sql = f.read()
        
        async with conn.transaction():
            await conn.execute(schema_sql)
    
    logger.info("Migrations complete")
