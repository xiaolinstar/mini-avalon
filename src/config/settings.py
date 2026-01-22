from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Env
    APP_ENV: str = "dev"  # dev, test, prod

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
    LOG_FILE: str | None = None
    SENTRY_DSN: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values):
        super().__init__(**values)
        # 自动处理测试环境的数据库
        if self.APP_ENV == "test" and "DATABASE_URL" not in os.environ:
            self.DATABASE_URL = "sqlite:///:memory:"


settings = Settings()
