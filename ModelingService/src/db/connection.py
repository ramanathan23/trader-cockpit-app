"""Database connection and migration utilities."""

import logging
from pathlib import Path

import asyncpg
from shared._sql_splitter import split_sql_statements

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
        schema_path = Path(__file__).parent / "schema.sql"
        await _execute_sql_file(conn, schema_path, timeout=timeout)

        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            for migration in sorted(migrations_dir.glob("*.sql")):
                await _execute_sql_file(conn, migration, timeout=timeout)
    
    logger.info("Migrations complete")


async def _execute_sql_file(conn: asyncpg.Connection, path: Path, *, timeout: float) -> None:
    sql = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    stmt_timeout = 86400.0 if timeout in (None, 0) else max(float(timeout), 300.0)
    logger.info("Applying %s (%d statements)", path.name, len(statements))
    for idx, stmt in enumerate(statements, 1):
        logger.debug("[%s %d/%d] %s", path.name, idx, len(statements), stmt.splitlines()[0][:120])
        await conn.execute(stmt, timeout=stmt_timeout)
