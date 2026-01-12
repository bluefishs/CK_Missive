"""
應用程式配置設定

安全性注意事項:
- 所有敏感資訊必須透過環境變數設定
- 不得在程式碼中硬編碼密碼、金鑰等敏感資料
- 生產環境必須設定 SECRET_KEY 和 DATABASE_URL

@version 2.0.0 - 安全性強化版
@date 2026-01-12
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import secrets
from pydantic import ConfigDict, Field, field_validator


def generate_default_secret_key() -> str:
    """生成開發環境用的隨機金鑰（每次啟動都不同，提醒設定正式金鑰）"""
    return f"dev_only_{secrets.token_hex(32)}"


class Settings(BaseSettings):
    # =========================================================================
    # 基本設定
    # =========================================================================
    APP_NAME: str = "乾坤測繪公文管理系統"
    DEBUG: bool = False
    DEVELOPMENT_MODE: bool = Field(
        default=True,
        description="開發模式標記，生產環境應設為 False"
    )

    # 安全金鑰 - 生產環境必須設定
    SECRET_KEY: str = Field(
        default_factory=generate_default_secret_key,
        description="JWT 簽名金鑰，生產環境必須設定固定值"
    )

    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # CORS 設定
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="允許的 CORS 來源，多個用逗號分隔"
    )

    # =========================================================================
    # 資料庫設定 - 必須透過環境變數設定
    # =========================================================================
    DATABASE_URL: str = Field(
        default="postgresql://localhost:5432/ck_documents",
        description="資料庫連線字串，格式: postgresql://user:pass@host:port/db"
    )
    POSTGRES_USER: str = Field(default="ck_user", description="PostgreSQL 使用者名稱")
    POSTGRES_PASSWORD: str = Field(default="", description="PostgreSQL 密碼")
    POSTGRES_DB: str = Field(default="ck_documents", description="PostgreSQL 資料庫名稱")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL 主機")
    POSTGRES_PORT: int = Field(default=5434, description="PostgreSQL 埠號")
    DATABASE_ECHO: bool = False

    # =========================================================================
    # JWT 設定
    # =========================================================================
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # =========================================================================
    # 開發模式選項
    # =========================================================================
    AUTH_DISABLED: bool = Field(
        default=False,
        description="設為 True 可繞過登入驗證，僅限開發使用，生產環境必須為 False"
    )

    # =========================================================================
    # Google OAuth & Calendar 設定
    # =========================================================================
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:3000/auth/callback",
        description="Google OAuth 回調 URI"
    )
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CREDENTIALS_PATH: str = "./GoogleCalendarAPIKEY.json"

    # Google OAuth 安全設定
    GOOGLE_ALLOWED_DOMAINS: str = Field(
        default="",
        description="允許的 Google 網域，多個用逗號分隔，空白表示允許所有（不建議）"
    )
    AUTO_ACTIVATE_NEW_USER: bool = Field(
        default=False,
        description="新帳號是否自動啟用，生產環境建議設為 False"
    )
    DEFAULT_USER_ROLE: str = "user"

    # =========================================================================
    # 日誌設定
    # =========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # =========================================================================
    # 前端設定
    # =========================================================================
    FRONTEND_HOST_PORT: int = 3000

    # =========================================================================
    # 驗證器
    # =========================================================================
    @field_validator('AUTH_DISABLED', mode='before')
    @classmethod
    def validate_auth_disabled(cls, v, info):
        """確保生產環境不會禁用認證"""
        if v and os.getenv('DEVELOPMENT_MODE', 'true').lower() == 'false':
            raise ValueError("AUTH_DISABLED 不能在生產環境中啟用")
        return v

    @field_validator('SECRET_KEY', mode='after')
    @classmethod
    def warn_default_secret_key(cls, v):
        """警告使用預設金鑰"""
        if v.startswith('dev_only_'):
            import logging
            logging.warning(
                "⚠️ 使用自動生成的 SECRET_KEY，請在 .env 中設定固定的 SECRET_KEY"
            )
        return v

    model_config = ConfigDict(
        env_file = "../.env",
        case_sensitive = True,
        extra = "ignore",
        env_file_encoding = "utf-8"
    )

    def get_database_url(self) -> str:
        """取得完整的資料庫連線字串"""
        if self.POSTGRES_PASSWORD:
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL


settings = Settings()
