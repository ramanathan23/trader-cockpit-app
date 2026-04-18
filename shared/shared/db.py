"""
Database pool creation and migration runner.

Single canonical implementation — all services import from here.
Handles dollar-quoted blocks, string literals, line/block comments
when splitting SQL migration files into individual statements.
"""

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


# ── SQL statement splitter ────────────────────────────────────────────────────

def _is_comment_only(stmt: str) -> bool:
    s = stmt
    while s:
        s = s.lstrip()
        if not s:
            return True
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1 :] if nl != -1 else ""
        elif s.startswith("/*"):
            end = s.find("*/", 2)
            s = s[end + 2 :] if end != -1 else ""
        else:
            return False
    return True


def split_sql_statements(sql: str) -> list[str]:
    """
    Split a SQL script into individual statements.

    Handles dollar-quoted blocks ($$...$$, $tag$...$tag$),
    single-quoted literals with '' escapes, line and block comments.
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)

    while i < n:
        ch = sql[i]

        # Line comment
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            j = sql.find("\n", i)
            j = n if j == -1 else j + 1
            buf.append(sql[i:j]); i = j; continue

        # Block comment
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            buf.append(sql[i:j]); i = j; continue

        # Dollar-quoted string
        if ch == "$":
            j = sql.find("$", i + 1)
            if j != -1:
                inner = sql[i + 1 : j]
                if all(c.isalnum() or c == "_" for c in inner):
                    tag = sql[i : j + 1]
                    end = sql.find(tag, j + 1)
                    if end != -1:
                        buf.append(sql[i : end + len(tag)])
                        i = end + len(tag)
                        continue

        # Single-quoted literal
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                    else:
                        j += 1; break
                else:
                    j += 1
            buf.append(sql[i:j]); i = j; continue

        # Statement terminator
        if ch == ";":
            buf.append(";")
            stmt = "".join(buf).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            buf = []; i += 1; continue

        buf.append(ch); i += 1

    remaining = "".join(buf).strip()
    if remaining and not _is_comment_only(remaining):
        statements.append(remaining)

    return statements


# ── Pool creation ─────────────────────────────────────────────────────────────

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


# ── Migration runner ──────────────────────────────────────────────────────────

async def run_migrations(
    pool: asyncpg.Pool,
    migrations_dir: Path,
    *,
    timeout: int | float | None = None,
    cancel_timescaledb_workers: bool = True,
) -> None:
    """
    Apply .sql files from *migrations_dir* in filename order, one statement at a time.

    *timeout* — per-statement cap in seconds.  0 or None → 24 h sentinel
    (asyncpg falls back to pool command_timeout when timeout=None, so we
    use an explicit large value for truly unlimited execution).
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
                    logger.error("%s stmt %d/%d failed:\n%s", migration.name, idx, len(statements), stmt[:400])
                    raise

            logger.info("Applied %s", migration.name)

    logger.info("All migrations applied")
