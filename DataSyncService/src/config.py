from pydantic import Field, model_validator

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):

    # ── Sync tuning ───────────────────────────────────────────────────────────
    sync_batch_size: int = Field(default=50)
    sync_batch_delay_s: float = Field(default=1.5)
    sync_1d_history_days: int = Field(default=1825)

    # ── Dhan ──────────────────────────────────────────────────────────────────
    dhan_client_id:    str = Field(default="")
    dhan_access_token: str = Field(default="")
    dhan_master_url:   str = Field(
        default="https://images.dhan.co/api-data/api-scrip-master.csv",
    )
    dhan_master_timeout_s: float = Field(default=30.0)

    # ── 1-minute sync (Dhan historical API) ───────────────────────────────────
    dhan_historical_url:   str = Field(default="https://api.dhan.co/v2/charts/intraday")
    dhan_1min_universe:    str = Field(default="all")  # all | fno
    dhan_1min_rate_per_sec: int = Field(default=2)   # max concurrent reqs/sec
    dhan_1min_persist_chunk_size: int = Field(default=60)
    dhan_daily_budget:      int = Field(default=10_000)  # Dhan API calls/day cap
    dhan_budget_safety:     int = Field(default=100)     # reserve buffer before stopping

    # Zerodha Kite Connect account sync.
    # Accounts are configured from the UI and stored in broker_accounts.
    zerodha_redirect_url: str = Field(
        default="http://localhost:8001/api/v1/zerodha/callback"
    )
    zerodha_return_url: str = Field(default="http://localhost:3000/")
    zerodha_api_base_url: str = Field(default="https://api.kite.trade")
    zerodha_login_base_url: str = Field(default="https://kite.zerodha.com/connect/login")
    zerodha_timeout_s: float = Field(default=20.0)
    zerodha_performance_start_date: str = Field(default="2026-04-01")

    @model_validator(mode="after")
    def _validate_dhan_credentials(self) -> "Settings":
        if not self.dhan_client_id or not self.dhan_access_token:
            import logging
            logging.getLogger(__name__).warning(
                "DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN not set — "
                "Dhan master sync will fail. Set them in .env or environment."
            )
        return self


settings = Settings()
