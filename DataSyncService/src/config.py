from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://trader:trader_secret@localhost:5432/trader_cockpit"

    # Dhan API credentials (required for 1-min historical data)
    # Get these from https://dhanhq.co → My Account → API Access
    dhan_client_id: str = ""
    dhan_access_token: str = ""

    # Max parallel Dhan API calls (stay under their rate limit)
    dhan_max_concurrency: int = 5

    # Sync tuning
    sync_batch_size: int = 50
    sync_batch_delay_s: float = 1.5   # seconds between yfinance daily batches

    log_level: str = "INFO"


settings = Settings()
