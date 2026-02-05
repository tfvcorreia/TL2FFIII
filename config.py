from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # TrueLayer
    truelayer_client_id: str
    truelayer_client_secret: str
    truelayer_token_url: str = "https://auth.truelayer.com/connect/token"
    truelayer_api_base: str = "https://api.truelayer.com/data/v1"
    
    # Firefly III
    firefly_url: str
    firefly_token: str
    
    # Database
    database_url: str = "sqlite:///./truelayer_firefly.db"
    
    # App Settings
    sync_interval_minutes: int = 60
    secret_key: str = "change-this-secret-key"
    debug: bool = False
    timezone: str = "Europe/London"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
