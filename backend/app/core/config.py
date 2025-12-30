"""
應用程式配置設定
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pydantic import ConfigDict, Field

class Settings(BaseSettings):
    # 基本設定
    APP_NAME: str = "乾坤測繪公文管理系統"
    DEBUG: bool = False
    SECRET_KEY: str = "default_secret_key_for_development_only"
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # **關鍵修復：新增 CORS_ORIGINS 設定**
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002"
    
    # PostgreSQL 資料庫設定
    DATABASE_URL: str = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"
    DATABASE_ECHO: bool = False
    
    # JWT 設定
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 開發模式選項
    AUTH_DISABLED: bool = Field(default=False, description="設為 True 可繞過登入驗證，僅限開發使用")
    
    # Google OAuth & Calendar 設定
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback"
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CREDENTIALS_PATH: str = "./GoogleCalendarAPIKEY.json"
    
    # 日誌設定
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # 前端端口設定
    FRONTEND_HOST_PORT: int = 3000
    
    model_config = ConfigDict(
        env_file = "../.env",
        case_sensitive = True,
        extra = "ignore",
        env_file_encoding = "utf-8"
    )

settings = Settings()
