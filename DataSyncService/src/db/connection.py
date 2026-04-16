import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _split_sql_statements(sql: str) -> list[str]:
    """
    Split a SQL script into individual statements.

    Handles:
      - Dollar-quoted blocks: $$ ... $$ and $tag$ ... $tag$
      - Single-quoted string literals with '' escapes
      - Line comments (--)
      - Block comments (/* ... */)
    """
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        # Line comment: consume to end of line
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            j = sql.find("\n", i)
            j = n if j == -1 else j + 1
            buf.append(sql[i:j])
            i = j
            continue

        # Block comment: consume to */
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            buf.append(sql[i:j])
            i = j
            continue

        # Dollar-quoted string: $tag$ ... $tag$
        # Tag is zero or more alphanumeric/underscore chars between two $
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

        # Single-quoted string literal
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2  # escaped ''
                    else:
                        j += 1
                        break
                else:
                    j += 1
            buf.append(sql[i:j])
            i = j
            continue

        # Statement terminator
        if ch == ";":
            buf.append(";")
            stmt = "".join(buf).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    # Trailing statement without a semicolon
    remaining = "".join(buf).strip()
    if remaining and not _is_comment_only(remaining):
        statements.append(remaining)

    return statements


def _is_comment_only(stmt: str) -> bool:
    """Return True if *stmt* contains only SQL comments and whitespace."""
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
        # Recycle idle connections every 5 minutes so Docker NAT drops are detected
        # before a stale connection is handed to application code.
        max_inactive_connection_lifetime=300,
        server_settings={
            # TCP keepalives: detect dead peers after ~75 s (idle 60 + 3×5)
            "tcp_keepalives_idle": "60",
            "tcp_keepalives_interval": "5",
            "tcp_keepalives_count": "3",
            # Hard cap on lock waits: surfaces contention as an error instead
            # of an invisible hang (30 s is generous for bulk-ingest workloads).
            "lock_timeout": "30000",
            # Kill transactions that are idle inside a BEGIN block for > 2 min.
            # Prevents leaked connections from holding locks forever.
            "idle_in_transaction_session_timeout": "120000",
        },
    )
    logger.info("Database pool created (min=%d, max=%d)", min_size, max_size)
    return pool


async def run_migrations(
    pool: asyncpg.Pool,
    *,
    timeout: int | float | None = None,
) -> None:
    """
    Apply schema DDL files in filename order, executing one statement at a time.

    Executing statement-by-statement (rather than the whole file at once) gives
    us per-statement error reporting and avoids one slow statement silently
    consuming the entire timeout budget before we know which SQL caused the issue.

    IMPORTANT — asyncpg timeout semantics:
      conn.execute(stmt, timeout=None) does NOT mean "unlimited". asyncpg falls
      back to the pool-level command_timeout (60 s by default) when timeout=None.
      We use a large explicit sentinel (24 h) to achieve truly unlimited execution
      for data-migration statements that may copy millions of rows.
    """
    # When the caller wants unlimited (timeout=0 or None), use a 24-hour sentinel
    # so asyncpg does not fall back to the pool's command_timeout.
    if timeout in (None, 0):
        stmt_timeout: float = 86400.0  # 24 h — effectively unlimited for DDL
        timeout_label = "unlimited (24h sentinel)"
    else:
        stmt_timeout = float(timeout)
        timeout_label = f"{stmt_timeout}s"

    async with pool.acquire() as conn:
        # DDL (CREATE INDEX, ALTER TABLE) must not be killed by the pool-level
        # lock_timeout=30s that protects application queries.
        await conn.execute("SET lock_timeout = 0")

        # Cancel any currently running TimescaleDB background workers so they
        # release chunk locks before DDL (CREATE INDEX, ALTER TABLE) runs.
        # We do NOT use timescaledb_pre_restore() — that disables TimescaleDB
        # hooks and breaks ALTER TABLE ... SET (timescaledb.compress, ...).
        # Cancelled workers reschedule themselves at their next interval; the
        # migration completes in seconds so they won't conflict again.
        try:
            n = await conn.fetchval("""
                SELECT count(pg_cancel_backend(pid))
                FROM pg_stat_activity
                WHERE application_name LIKE 'TimescaleDB%'
                  AND pid <> pg_backend_pid()
            """, timeout=30.0)
            if n:
                logger.info("Cancelled %d running TimescaleDB background worker(s)", n)
        except Exception as exc:
            logger.warning("Could not cancel TimescaleDB workers (non-fatal): %s", exc)

        for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            sql = migration.read_text(encoding="utf-8")
            statements = _split_sql_statements(sql)
            logger.info(
                "Applying migration %s (%d statements, timeout=%s)",
                migration.name,
                len(statements),
                timeout_label,
            )
            for idx, stmt in enumerate(statements, 1):
                first_line = stmt.split("\n")[0].strip()[:120]
                logger.info(
                    "Migration %s [%d/%d]: %s",
                    migration.name, idx, len(statements), first_line,
                )
                try:
                    await conn.execute(stmt, timeout=stmt_timeout)
                except asyncpg.DuplicateObjectError:
                    logger.debug(
                        "Migration %s stmt %d: object already exists, skipping",
                        migration.name,
                        idx,
                    )
                except Exception:
                    logger.error(
                        "Migration %s statement %d/%d failed:\n%s",
                        migration.name,
                        idx,
                        len(statements),
                        stmt[:400],
                    )
                    raise
            logger.info("Applied migration %s", migration.name)

    logger.info("All migrations applied")
