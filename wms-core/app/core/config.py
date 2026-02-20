from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "WMS API"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./wms.db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30 days
    
    class Config:
        env_file = ".env"


settings = Settings()
