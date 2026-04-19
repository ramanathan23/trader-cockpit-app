"""
Database pool creation and migration runner.

Single canonical implementation — all services import from here.
Handles dollar-quoted blocks, string literals, line/block comments
when splitting SQL migration files into individual statements.
"""

from ._pool_factory import create_pool
from ._migrations import run_migrations
from ._sql_splitter import split_sql_statements, _is_comment_only

__all__ = [
    "create_pool",
    "run_migrations",
    "split_sql_statements",
    "_is_comment_only",
]
