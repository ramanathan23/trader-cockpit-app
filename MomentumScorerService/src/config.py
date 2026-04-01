from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://trader:trader_secret@localhost:5432/trader_cockpit"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"

    # How many daily bars to load per symbol for scoring
    score_lookback_bars: int = 200


settings = Settings()
