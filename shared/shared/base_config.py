"""
Common settings fields shared across all backend services.

Each service subclasses BaseServiceSettings and adds its own fields.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://trader:trader_secret@localhost:5432/trader_cockpit",
    )
    db_pool_min_size: int = Field(default=5)
    db_pool_max_size: int = Field(default=20)
    db_command_timeout: int = Field(default=60)
    db_migration_timeout: int = Field(default=0)

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379")

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
