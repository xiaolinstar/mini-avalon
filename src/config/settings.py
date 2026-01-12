import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Flask
    SECRET_KEY: str = "dev-key"
    FLASK_DEBUG: bool = True
    
    # WeChat
    WECHAT_TOKEN: str = ""
    WECHAT_APPID: str = ""
    WECHAT_AES_KEY: str = ""
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost/avalon_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "TEXT"  # TEXT or JSON
    LOG_FILE: Optional[str] = None

    # Env
    APP_ENV: str = "dev"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'dev')}",
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
