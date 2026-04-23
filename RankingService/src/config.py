from pydantic import Field

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):
    db_pool_min_size: int = Field(default=3)
    db_pool_max_size: int = Field(default=10)
    score_concurrency: int = Field(default=20)
    min_adv_crores: float = Field(default=1.0)
    modeling_service_url: str = Field(default="http://modeling:8000")
    enable_comfort_scoring: bool = Field(default=True)


settings = Settings()
