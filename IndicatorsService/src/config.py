from pydantic import Field

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):
    db_pool_min_size: int = Field(default=3)
    db_pool_max_size: int = Field(default=10)

    lookback_bars: int = Field(default=252)
    min_bars: int = Field(default=30)
    concurrency: int = Field(default=10)

    nifty500_benchmark: str = Field(default="NIFTY500")
    min_adv_crores: float = Field(default=1.0)

    vcp_min_contractions: int = Field(default=2)
    rect_lookback: int = Field(default=40)
    rect_max_range_pct: float = Field(default=0.10)


settings = Settings()
