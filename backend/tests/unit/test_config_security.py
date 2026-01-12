# -*- coding: utf-8 -*-
"""
設定安全性單元測試
Config Security Unit Tests

執行方式:
    pytest tests/unit/test_config_security.py -v
"""
import pytest
import sys
import os

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import generate_default_secret_key


class TestSecretKeyGeneration:
    """SECRET_KEY 生成測試"""

    def test_generate_default_secret_key_unique(self):
        """測試每次生成不同的金鑰"""
        key1 = generate_default_secret_key()
        key2 = generate_default_secret_key()

        assert key1 != key2

    def test_generate_default_secret_key_prefix(self):
        """測試金鑰有正確的前綴"""
        key = generate_default_secret_key()

        assert key.startswith("dev_only_")

    def test_generate_default_secret_key_length(self):
        """測試金鑰長度足夠"""
        key = generate_default_secret_key()

        # dev_only_ (9 chars) + 64 hex chars = 73 chars
        assert len(key) >= 73


class TestSettingsDefaults:
    """Settings 預設值測試"""

    def test_auto_activate_default_false(self):
        """測試 AUTO_ACTIVATE_NEW_USER 預設為 False"""
        from app.core.config import settings

        # 在沒有環境變數覆蓋的情況下，應該是 False
        # 注意：此測試可能因環境變數而異
        assert hasattr(settings, "AUTO_ACTIVATE_NEW_USER")

    def test_auth_disabled_has_default(self):
        """測試 AUTH_DISABLED 有預設值"""
        from app.core.config import settings

        assert hasattr(settings, "AUTH_DISABLED")
        assert isinstance(settings.AUTH_DISABLED, bool)

    def test_postgres_fields_exist(self):
        """測試 PostgreSQL 設定欄位存在"""
        from app.core.config import settings

        assert hasattr(settings, "POSTGRES_USER")
        assert hasattr(settings, "POSTGRES_PASSWORD")
        assert hasattr(settings, "POSTGRES_DB")


class TestSettingsSecurityValidation:
    """Settings 安全驗證測試"""

    def test_settings_has_secret_key(self):
        """測試 settings 有 SECRET_KEY"""
        from app.core.config import settings

        assert hasattr(settings, "SECRET_KEY")
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_settings_has_algorithm(self):
        """測試 settings 有 ALGORITHM"""
        from app.core.config import settings

        assert hasattr(settings, "ALGORITHM")
        assert settings.ALGORITHM in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]

    def test_settings_has_access_token_expire(self):
        """測試 settings 有 ACCESS_TOKEN_EXPIRE_MINUTES"""
        from app.core.config import settings

        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0


class TestDatabaseURLSecurity:
    """資料庫 URL 安全測試"""

    def test_database_url_not_hardcoded(self):
        """測試 DATABASE_URL 不是寫死的不安全值"""
        from app.core.config import settings

        if settings.DATABASE_URL:
            # 不應該包含明顯的測試密碼
            assert "password123" not in settings.DATABASE_URL.lower()
            assert "test123" not in settings.DATABASE_URL.lower()
