"""
Persistence and queries for the daily_scores table.
"""

import asyncpg

from ._score_reads import ScoreReadMixin
from ._score_reads_balanced import ScoreReadBalancedMixin
from ._score_writes import ScoreWriteMixin


class ScoreRepository(ScoreWriteMixin, ScoreReadMixin, ScoreReadBalancedMixin):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
