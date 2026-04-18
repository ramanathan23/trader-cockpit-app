from pydantic import Field

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):

    db_pool_min_size: int = Field(default=3)
    db_pool_max_size: int = Field(default=10)

    # ── Scoring ───────────────────────────────────────────────────────────────
    score_lookback_bars: int = Field(default=200)
    score_min_bars: int = Field(default=30)
    score_concurrency: int = Field(default=10)

    # ── Indicator parameters ──────────────────────────────────────────────────
    rsi_period: int = Field(default=14)
    macd_fast: int = Field(default=12)
    macd_slow: int = Field(default=26)
    macd_signal: int = Field(default=9)
    vol_avg_period: int = Field(default=20)

    # ── Benchmark ─────────────────────────────────────────────────────────────
    nifty500_benchmark: str = Field(default="NIFTY500")

    # ── Quality filters ───────────────────────────────────────────────────────
    min_avg_daily_turnover: float = Field(default=10_000_000)


settings = Settings()
