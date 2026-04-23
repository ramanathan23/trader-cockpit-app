"""Re-exports from the shared DB library — keeps service imports unchanged."""

from pathlib import Path

from shared.db import create_pool, run_migrations as _run_migrations

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations(pool, *, timeout=None):
    await _run_migrations(pool, MIGRATIONS_DIR, timeout=timeout)


__all__ = ["create_pool", "run_migrations"]
