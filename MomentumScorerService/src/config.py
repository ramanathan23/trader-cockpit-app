from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://trader:trader_secret@localhost:5432/trader_cockpit",
        description="PostgreSQL/TimescaleDB connection DSN",
    )
    db_pool_min_size: int = Field(default=3, description="asyncpg pool minimum connections")
    db_pool_max_size: int = Field(default=10, description="asyncpg pool maximum connections")
    db_command_timeout: int = Field(default=60, description="DB command timeout in seconds")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )

    log_level: str = Field(default="INFO", description="Python root logging level")

    # ── Scoring ───────────────────────────────────────────────────────────────
    score_lookback_bars: int = Field(
        default=200, description="OHLCV bars loaded per symbol for indicator calculation"
    )
    score_min_bars: int = Field(
        default=30, description="Minimum bars required to produce a valid score"
    )
    score_concurrency: int = Field(
        default=10, description="Maximum parallel CPU-bound scoring tasks (asyncio.to_thread)"
    )

    # ── Indicator parameters ──────────────────────────────────────────────────
    rsi_period: int = Field(default=14, description="RSI lookback window")
    macd_fast: int = Field(default=12, description="MACD fast EMA period")
    macd_slow: int = Field(default=26, description="MACD slow EMA period")
    macd_signal: int = Field(default=9, description="MACD signal EMA period")
    roc_period: int = Field(default=10, description="Rate-of-Change lookback window")
    vol_avg_period: int = Field(default=20, description="Volume ratio rolling average window")

    # ── Score weights (must sum to 1.0) ───────────────────────────────────────
    weight_rsi: float = Field(default=0.30, description="RSI component weight")
    weight_macd: float = Field(default=0.30, description="MACD component weight")
    weight_roc: float = Field(default=0.25, description="ROC component weight")
    weight_vol: float = Field(default=0.15, description="Volume ratio component weight")

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "Settings":
        total = self.weight_rsi + self.weight_macd + self.weight_roc + self.weight_vol
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Score weights must sum to 1.0, got {total:.4f}. "
                "Check WEIGHT_RSI, WEIGHT_MACD, WEIGHT_ROC, WEIGHT_VOL."
            )
        return self


settings = Settings()
