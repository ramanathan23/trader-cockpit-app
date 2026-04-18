from pydantic import Field

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):

    db_metrics_recompute_timeout: int = Field(default=0)

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


settings = Settings()
