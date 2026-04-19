"""Migration runner."""

import logging
from pathlib import Path

import asyncpg

from ._sql_splitter import split_sql_statements

logger = logging.getLogger(__name__)


async def run_migrations(
    pool: asyncpg.Pool,
    migrations_dir: Path,
    *,
    timeout: int | float | None = None,
    cancel_timescaledb_workers: bool = True,
) -> None:
    """
    Apply .sql files from *migrations_dir* in filename order, one statement at a time.

    *timeout* — per-statement cap in seconds.  0 or None → 24 h sentinel.
    """
    stmt_timeout: float = 86400.0 if timeout in (None, 0) else float(timeout)

    async with pool.acquire() as conn:
        await conn.execute("SET lock_timeout = 0")

        if cancel_timescaledb_workers:
            try:
                n = await conn.fetchval("""
                    SELECT count(pg_cancel_backend(pid))
                    FROM pg_stat_activity
                    WHERE application_name LIKE 'TimescaleDB%'
                      AND pid <> pg_backend_pid()
                """, timeout=30.0)
                if n:
                    logger.info("Cancelled %d TimescaleDB background worker(s)", n)
            except Exception as exc:
                logger.warning("Could not cancel TimescaleDB workers (non-fatal): %s", exc)

        for migration in sorted(migrations_dir.glob("*.sql")):
            sql = migration.read_text(encoding="utf-8")
            statements = split_sql_statements(sql)
            logger.info("Applying %s (%d statements)", migration.name, len(statements))

            for idx, stmt in enumerate(statements, 1):
                first_line = stmt.split("\n")[0].strip()[:120]
                logger.debug("[%s %d/%d] %s", migration.name, idx, len(statements), first_line)
                try:
                    await conn.execute(stmt, timeout=stmt_timeout)
                except asyncpg.DuplicateObjectError:
                    logger.debug("%s stmt %d: object exists, skipping", migration.name, idx)
                except Exception:
                    logger.error(
                        "%s stmt %d/%d failed:\n%s",
                        migration.name, idx, len(statements), stmt[:400],
                    )
                    raise

            logger.info("Applied %s", migration.name)

    logger.info("All migrations applied")
