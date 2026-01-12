# -*- coding: utf-8 -*-
"""
認證服務單元測試
AuthService Unit Tests

執行方式:
    pytest tests/unit/test_auth_service.py -v
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.auth_service import AuthService


class TestPasswordHashing:
    """密碼雜湊測試"""

    def test_hash_password_returns_different_hash(self):
        """測試相同密碼產生不同雜湊（因為 salt）"""
        password = "test_password_123"
        hash1 = AuthService.get_password_hash(password)
        hash2 = AuthService.get_password_hash(password)

        # 每次產生的雜湊應該不同（因為 bcrypt 使用隨機 salt）
        assert hash1 != hash2

    def test_hash_password_is_not_plaintext(self):
        """測試雜湊不是明文"""
        password = "test_password_123"
        hashed = AuthService.get_password_hash(password)

        assert password not in hashed
        assert hashed.startswith("$2b$")  # bcrypt 格式

    def test_verify_password_correct(self):
        """測試正確密碼驗證"""
        password = "test_password_123"
        hashed = AuthService.get_password_hash(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """測試錯誤密碼驗證"""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = AuthService.get_password_hash(password)

        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_fails(self):
        """測試空密碼驗證失敗"""
        password = "test_password_123"
        hashed = AuthService.get_password_hash(password)

        assert AuthService.verify_password("", hashed) is False


class TestTokenGeneration:
    """令牌生成測試"""

    def test_generate_token_jti_unique(self):
        """測試 JTI 唯一性"""
        jti1 = AuthService.generate_token_jti()
        jti2 = AuthService.generate_token_jti()

        assert jti1 != jti2
        assert len(jti1) == 36  # UUID 格式長度

    def test_create_access_token_valid(self):
        """測試建立有效存取令牌"""
        data = {"sub": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        assert token is not None
        assert len(token) > 0
        assert "." in token  # JWT 格式: header.payload.signature

    def test_create_access_token_with_expiry(self):
        """測試建立自訂過期時間的令牌"""
        data = {"sub": "123"}
        expires = timedelta(hours=1)
        token = AuthService.create_access_token(data, expires_delta=expires)

        # 驗證令牌有效
        payload = AuthService.verify_token(token)
        assert payload is not None
        assert payload.get("sub") == "123"

    def test_verify_token_valid(self):
        """測試驗證有效令牌"""
        data = {"sub": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        payload = AuthService.verify_token(token)

        assert payload is not None
        assert payload.get("sub") == "123"
        assert payload.get("email") == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_verify_token_invalid(self):
        """測試驗證無效令牌"""
        invalid_token = "invalid.token.here"

        payload = AuthService.verify_token(invalid_token)

        assert payload is None

    def test_create_refresh_token(self):
        """測試建立刷新令牌"""
        token = AuthService.create_refresh_token()

        assert token is not None
        assert len(token) >= 32  # 至少 32 字元


class TestDomainWhitelist:
    """網域白名單測試"""

    def test_check_email_domain_no_whitelist(self, monkeypatch):
        """測試無白名單時允許所有網域"""
        # 模擬空白名單
        from app.core import config
        monkeypatch.setattr(config.settings, "GOOGLE_ALLOWED_DOMAINS", "")

        assert AuthService.check_email_domain("user@gmail.com") is True
        assert AuthService.check_email_domain("user@company.com") is True

    def test_check_email_domain_in_whitelist(self, monkeypatch):
        """測試網域在白名單內"""
        from app.core import config
        monkeypatch.setattr(config.settings, "GOOGLE_ALLOWED_DOMAINS", "company.com,example.org")

        assert AuthService.check_email_domain("user@company.com") is True
        assert AuthService.check_email_domain("user@example.org") is True

    def test_check_email_domain_not_in_whitelist(self, monkeypatch):
        """測試網域不在白名單內"""
        from app.core import config
        monkeypatch.setattr(config.settings, "GOOGLE_ALLOWED_DOMAINS", "company.com")

        assert AuthService.check_email_domain("user@gmail.com") is False
        assert AuthService.check_email_domain("user@other.com") is False


class TestAutoActivation:
    """自動啟用新帳號測試"""

    def test_should_auto_activate_true(self, monkeypatch):
        """測試設定為自動啟用"""
        from app.core import config
        monkeypatch.setattr(config.settings, "AUTO_ACTIVATE_NEW_USER", True)

        assert AuthService.should_auto_activate() is True

    def test_should_auto_activate_false(self, monkeypatch):
        """測試設定為不自動啟用"""
        from app.core import config
        monkeypatch.setattr(config.settings, "AUTO_ACTIVATE_NEW_USER", False)

        assert AuthService.should_auto_activate() is False


class TestDefaultRole:
    """預設角色測試"""

    def test_get_default_user_role(self, monkeypatch):
        """測試取得預設角色"""
        from app.core import config
        monkeypatch.setattr(config.settings, "DEFAULT_USER_ROLE", "viewer")

        assert AuthService.get_default_user_role() == "viewer"

    def test_get_default_user_role_fallback(self, monkeypatch):
        """測試預設角色回退值"""
        from app.core import config
        monkeypatch.setattr(config.settings, "DEFAULT_USER_ROLE", "")

        assert AuthService.get_default_user_role() == "user"


class TestDefaultPermissions:
    """預設權限測試"""

    def test_get_default_permissions_format(self):
        """測試預設權限格式"""
        permissions = AuthService.get_default_permissions()

        import json
        parsed = json.loads(permissions)

        assert isinstance(parsed, list)
        assert "documents:read" in parsed
        assert "projects:read" in parsed
