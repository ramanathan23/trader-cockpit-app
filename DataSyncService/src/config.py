from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://trader:trader_secret@localhost:5432/trader_cockpit",
        description="PostgreSQL/TimescaleDB connection DSN",
    )
    db_pool_min_size: int = Field(default=5, description="asyncpg pool minimum connections")
    db_pool_max_size: int = Field(default=20, description="asyncpg pool maximum connections")
    db_command_timeout: int = Field(default=60, description="DB command timeout in seconds")
    db_migration_timeout: int = Field(
        default=0,
        description=(
            "Per-statement migration timeout in seconds. "
            "0 (default) disables the timeout — migrations run statement-by-statement "
            "so individual slow DDL (e.g. a data-copy migration) won't be killed mid-way. "
            "Set to a positive value only if you want a hard cap per statement."
        ),
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL (used for pub/sub and caching)",
    )

    # ── Sync tuning ───────────────────────────────────────────────────────────
    sync_batch_size: int = Field(
        default=50, description="Symbols per yfinance download batch"
    )
    sync_batch_delay_s: float = Field(
        default=1.5, description="Seconds to wait between consecutive yfinance batches"
    )
    sync_1d_history_days: int = Field(
        default=1825, description="Daily bar lookback depth in days (~5 years)"
    )

    # ── Dhan ──────────────────────────────────────────────────────────────────
    dhan_client_id:    str = Field(default="", description="Dhan client ID")
    dhan_access_token: str = Field(default="", description="Dhan access token")
    dhan_master_url:   str = Field(
        default="https://images.dhan.co/api-data/api-scrip-master.csv",
        description="URL of the Dhan instrument master CSV (published daily)",
    )
    dhan_master_timeout_s: float = Field(
        default=30.0,
        description="HTTP timeout in seconds for the Dhan master CSV download",
    )

    log_level: str = Field(default="INFO", description="Python root logging level")


settings = Settings()
