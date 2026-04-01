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

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL (used for pub/sub and caching)",
    )

    # ── Dhan API ──────────────────────────────────────────────────────────────
    # Get credentials from https://dhanhq.co → My Account → API Access
    dhan_client_id: str = Field(default="", description="Dhan API client ID")
    dhan_access_token: str = Field(default="", description="Dhan API access token")
    dhan_max_concurrency: int = Field(
        default=5, description="Max parallel Dhan API calls (stay under rate limit)"
    )
    dhan_security_master_url: str = Field(
        default="https://images.dhan.co/api-data/api-scrip-master.csv",
        description="URL for the Dhan NSE scrip master CSV download",
    )
    dhan_master_ttl_hours: int = Field(
        default=24, description="Hours before the cached security master is re-downloaded"
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
    sync_1m_history_days: int = Field(
        default=90, description="1-minute bar lookback depth in days (Dhan API max)"
    )

    log_level: str = Field(default="INFO", description="Python root logging level")


settings = Settings()
