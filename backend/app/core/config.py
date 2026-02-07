"""
應用程式配置設定

安全性注意事項:
- 所有敏感資訊必須透過環境變數設定
- 不得在程式碼中硬編碼密碼、金鑰等敏感資料
- 生產環境必須設定 SECRET_KEY 和 DATABASE_URL

設定檔位置 (Single Source of Truth):
- 統一使用專案根目錄的 .env 檔案
- 後端目錄不應有獨立的 .env 檔案

@version 2.1.0 - 設定統一化
@date 2026-01-18
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import sys
import secrets
import logging
from pathlib import Path
from pydantic import ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


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
    # ⚠️ 安全性修正 (2026-02-02): 移除硬編碼密碼
    # =========================================================================
    DATABASE_URL: str = Field(
        default="",
        description="資料庫連線字串，格式: postgresql://user:pass@host:port/db，必須透過 .env 設定"
    )
    POSTGRES_USER: str = Field(default="", description="PostgreSQL 使用者名稱，必須透過 .env 設定")
    POSTGRES_PASSWORD: str = Field(default="", description="PostgreSQL 密碼，必須透過 .env 設定")
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
    # Redis 設定
    # =========================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 連線字串，用於 AI 快取與統計持久化"
    )

    # =========================================================================
    # 日誌設定
    # =========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # =========================================================================
    # API 速率限制設定
    # =========================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="每分鐘請求上限"
    )
    RATE_LIMIT_PER_DAY: int = Field(
        default=10000,
        description="每日請求上限"
    )

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
    def validate_secret_key(cls, v, info):
        """驗證 SECRET_KEY 安全性"""
        if v.startswith('dev_only_'):
            # 生產環境拒絕啟動（支援 false/0/no 等常見否定值）
            dev_mode = os.getenv('DEVELOPMENT_MODE', 'true').lower().strip()
            if dev_mode not in ('true', '1', 'yes'):
                raise ValueError(
                    "生產環境必須在 .env 中設定固定的 SECRET_KEY，"
                    "不得使用自動生成的開發金鑰"
                )
            import logging
            logging.warning(
                "⚠️ 使用自動生成的 SECRET_KEY，重啟後所有已發行 token 將失效。"
                "請在 .env 中設定固定的 SECRET_KEY"
            )
        return v

    model_config = ConfigDict(
        # 自動搜尋 .env 檔案：優先使用專案根目錄
        env_file = [
            "../.env",           # 從 backend/ 目錄運行時
            "../../.env",        # 從 backend/app/ 目錄運行時
            ".env",              # 當前目錄 (Docker 容器內)
        ],
        case_sensitive = True,
        extra = "ignore",
        env_file_encoding = "utf-8"
    )

    def get_database_url(self) -> str:
        """取得完整的資料庫連線字串"""
        if self.POSTGRES_PASSWORD:
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL

    def validate_database_config(self) -> bool:
        """驗證資料庫設定是否完整"""
        required_fields = ['DATABASE_URL', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        missing = []
        for field in required_fields:
            value = getattr(self, field, None)
            if not value or value == '':
                missing.append(field)

        if missing:
            logger.error(
                f"🔴 資料庫設定不完整，缺少: {', '.join(missing)}。"
                f"\n   請在專案根目錄的 .env 檔案中設定這些必要的環境變數。"
                f"\n   ⚠️ 安全提醒: 請勿在程式碼中硬編碼密碼！"
            )
            return False
        return True

    def validate_security_config(self) -> bool:
        """驗證安全性設定"""
        issues = []

        # 檢查是否使用開發用金鑰
        if self.SECRET_KEY.startswith('dev_only_'):
            issues.append("SECRET_KEY 使用自動生成的開發金鑰")

        # 檢查生產環境設定
        if not self.DEVELOPMENT_MODE:
            if self.AUTH_DISABLED:
                issues.append("生產環境禁用了認證")
            if not self.GOOGLE_ALLOWED_DOMAINS:
                issues.append("生產環境未設定 Google 網域白名單")

        if issues:
            for issue in issues:
                logger.warning(f"⚠️ 安全性警告: {issue}")
            return False
        return True


# 初始化設定並驗證
settings = Settings()

# 啟動時驗證資料庫設定
if not settings.validate_database_config():
    logger.warning(
        "⚠️ 資料庫設定可能不完整，請檢查專案根目錄的 .env 檔案。"
        "\n   預期位置: CK_Missive/.env"
    )
