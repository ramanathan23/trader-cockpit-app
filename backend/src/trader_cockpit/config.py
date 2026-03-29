"""Application settings — loaded from environment variables via pydantic-settings."""
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Trader Cockpit"
    debug: bool = False
    environment: str = "production"

    # ── Security ─────────────────────────────────────────────────────────────
    jwt_secret: str = Field(..., min_length=32)
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(..., description="asyncpg DSN e.g. postgresql+asyncpg://user:pass@host/db")
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_quote_ttl_seconds: int = 30       # Quote cache TTL
    redis_greeks_ttl_seconds: int = 30      # Option Greeks cache TTL
    redis_session_key: str = "dhan:token"

    # ── Dhan ─────────────────────────────────────────────────────────────────
    dhan_client_id: str = Field(..., description="Dhan client ID (from DhanHQ)")
    dhan_access_token: str = Field(default="", description="Initial token; renewed nightly")
    dhan_base_url: str = "https://api.dhan.co/v2"
    dhan_ws_feed_url: str = "wss://api-feed.dhan.co"
    dhan_ws_order_url: str = "wss://api-order-update.dhan.co"

    # ── Risk defaults ─────────────────────────────────────────────────────────
    default_intraday_risk_pct: float = 0.5   # 0.5% of capital per trade
    default_cnc_risk_pct: float = 1.0        # 1.0% of capital per trade
    default_daily_loss_limit: float = 5000.0  # ₹5,000

    # ── Market hours (IST) ────────────────────────────────────────────────────
    market_open_hour: int = 9
    market_open_minute: int = 15
    market_close_hour: int = 15
    market_close_minute: int = 30
    eod_conversion_deadline_hour: int = 15
    eod_conversion_deadline_minute: int = 20

    # ── Token renewal ─────────────────────────────────────────────────────────
    token_renewal_hour: int = 21    # 9 PM IST
    token_renewal_minute: int = 0

    # ── Position polling ──────────────────────────────────────────────────────
    position_poll_interval_seconds: int = 4

    @field_validator("database_url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use postgresql+asyncpg:// scheme")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
