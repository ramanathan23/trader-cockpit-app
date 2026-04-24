from pydantic import Field, model_validator

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):

    db_pool_min_size: int = Field(default=2)
    db_pool_max_size: int = Field(default=10)

    # ── Dhan ──────────────────────────────────────────────────────────────────
    dhan_client_id:    str   = Field(default="")
    dhan_access_token: str   = Field(default="")
    dhan_ws_batch_size: int  = Field(default=500)
    dhan_reconnect_delay_s: float = Field(default=5.0)

    @model_validator(mode="after")
    def _validate_dhan_credentials(self) -> "Settings":
        if not self.dhan_client_id or not self.dhan_access_token:
            import logging
            logging.getLogger(__name__).warning(
                "DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN not set — "
                "live feed will fail to connect."
            )
        return self

    # ── Market hours (IST) ────────────────────────────────────────────────────
    market_open_h:  int = Field(default=9)
    market_open_m:  int = Field(default=15)
    market_close_h: int = Field(default=15)
    market_close_m: int = Field(default=30)
    candle_minutes: int = Field(default=5)

    # ── Signal thresholds ─────────────────────────────────────────────────────
    drive_candles:          int   = Field(default=5)
    drive_min_body_ratio:   float = Field(default=0.6)
    drive_confirmed_thresh: float = Field(default=0.70)
    drive_weak_thresh:      float = Field(default=0.50)

    # ── Level breakout vol ratios ─────────────────────────────────────────────
    orb_vol_ratio:          float = Field(default=1.3)
    week52_vol_ratio:       float = Field(default=2.0)
    camarilla_vol_ratio:    float = Field(default=1.3)
    vwap_vol_ratio:         float = Field(default=1.3)
    vwap_hysteresis_min:    int   = Field(default=2)
    range_lookback:         int   = Field(default=5)
    range_vol_ratio:        float = Field(default=1.5)
    range_max_pct:          float = Field(default=0.02)

    # ── Noise filters ─────────────────────────────────────────────────────────
    min_adv_cr:             float = Field(default=5.0)
    cluster_max_per_candle: int   = Field(default=5)

    # ── Multi-timeframe confluence ────────────────────────────────────────────
    confluence_15m_candles: int   = Field(default=3)
    confluence_1h_candles:  int   = Field(default=12)
    confluence_min_move_pct: float = Field(default=0.15)

    # ── Gap detector ──────────────────────────────────────────────────────────────
    gap_min_pct:            float = Field(default=1.5)

    # ── Camarilla ─────────────────────────────────────────────────────────────
    cam_narrow_range_pct:   float = Field(default=0.03)  # H4-L4/prev_close ≤ → narrow (breakout)

    # ── Candle writer ─────────────────────────────────────────────────────────
    candle_write_batch_size: int   = Field(default=100)
    candle_write_flush_s:    float = Field(default=5.0)


settings = Settings()
