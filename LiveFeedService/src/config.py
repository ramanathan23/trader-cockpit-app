from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url:        str = Field(
        default="postgresql://trader:trader_secret@localhost:5432/trader_cockpit",
    )
    db_pool_min_size:    int   = Field(default=2)
    db_pool_max_size:    int   = Field(default=10)
    db_command_timeout:  int   = Field(default=60)
    db_migration_timeout: int  = Field(default=0)

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379")

    # ── Dhan ──────────────────────────────────────────────────────────────────
    dhan_client_id:    str   = Field(default="")
    dhan_access_token: str   = Field(default="")
    # Max instruments per WebSocket connection (Dhan limit).
    dhan_ws_batch_size: int  = Field(default=1000)
    # Seconds to wait before reconnecting after a WebSocket drop.
    dhan_reconnect_delay_s: float = Field(default=5.0)

    # ── Market hours (IST) ────────────────────────────────────────────────────
    market_open_h:  int = Field(default=9,  description="Market open hour IST")
    market_open_m:  int = Field(default=15, description="Market open minute IST")
    market_close_h: int = Field(default=15, description="Market close hour IST")
    market_close_m: int = Field(default=30, description="Market close minute IST")
    candle_minutes: int = Field(default=5,  description="Candle size in minutes")

    # ── Signal thresholds ─────────────────────────────────────────────────────
    drive_candles:          int   = Field(default=5,    description="Candles used for open drive detection")
    drive_min_body_ratio:   float = Field(default=0.6,  description="Min candle body / range for drive conviction")
    drive_confirmed_thresh: float = Field(default=0.70, description="Confidence >= this → CONFIRMED")
    drive_weak_thresh:      float = Field(default=0.50, description="Confidence >= this → WEAK")

    spike_window:           int   = Field(default=20,   description="Rolling window (candles) for spike baselines")
    spike_vol_ratio:        float = Field(default=3.0,  description="volume / avg_volume threshold for spike")
    spike_price_pct:        float = Field(default=1.5,  description="% price move threshold for shock")

    # ── Noise filters ─────────────────────────────────────────────────────────
    # Instruments with ADV below this (in Cr) are skipped for ALL spike/breakout signals.
    min_adv_cr:             float = Field(default=5.0,  description="Minimum 20-day ADV in Cr to emit signals")
    # If more than this many signals of the same type fire in the same candle boundary, extras are dropped.
    cluster_max_per_candle: int   = Field(default=5,    description="Max same-type signals per candle boundary")

    # ── Multi-timeframe confluence ────────────────────────────────────────────
    # Number of 5-min candles that make up the 15-min and 1-hr confluence windows.
    confluence_15m_candles: int   = Field(default=3,  description="5-min candles per 15-min confluence window")
    confluence_1h_candles:  int   = Field(default=12, description="5-min candles per 1-hr confluence window")

    # Candle writer batch: flush to DB every N candles or every T seconds.
    candle_write_batch_size: int   = Field(default=100)
    candle_write_flush_s:    float = Field(default=5.0)

    log_level: str = Field(default="INFO")


settings = Settings()
