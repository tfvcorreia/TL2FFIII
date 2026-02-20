from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # TrueLayer
    truelayer_client_id: str = ""  # Make optional with default
    truelayer_client_secret: str = ""  # Make optional with default
    truelayer_token_url: str = "https://auth.truelayer.com/connect/token"
    truelayer_api_base: str = "https://api.truelayer.com/data/v1"
    
    # Firefly III - Make optional so they can be set via UI
    firefly_url: str = ""  # Empty default - will be set via settings page
    firefly_token: str = ""  # Empty default - will be set via settings page
    
    # Database
    database_url: str = "sqlite:////app/data/truelayer_firefly.db"  # Fixed path for Docker
    
    # App Settings
    sync_interval_minutes: int = 60
    secret_key: str = "change-this-secret-key"
    debug: bool = False
    timezone: str = "Europe/London"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
