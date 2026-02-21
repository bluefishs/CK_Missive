# -*- coding: utf-8 -*-
"""
AuthService 單元測試

測試範圍:
- 密碼驗證: verify_password, get_password_hash
- Token 管理: create_access_token, create_refresh_token, verify_token
- 密碼強度驗證: validate_password_strength
- Cookie 管理: set_auth_cookies, clear_auth_cookies
- Session 管理: revoke_session, revoke_all_sessions
- 靜態工具方法: check_permission, check_admin_permission
- 網域白名單: check_email_domain

測試策略: Mock AsyncSession 和 jwt，不使用真實資料庫。

v1.0.0 - 2026-02-21
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """建立 mock AsyncSession"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_user():
    """建立模擬使用者實體"""
    from app.extended.models import User

    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.username = "testuser"
    user.full_name = "Test User"
    user.password_hash = "$2b$12$dummy_bcrypt_hash"
    user.is_active = True
    user.is_admin = False
    user.is_superuser = False
    user.role = "user"
    user.permissions = '["documents:read", "projects:read"]'
    user.google_id = None
    user.avatar_url = None
    user.auth_provider = "local"
    user.login_count = 5
    user.last_login = datetime(2026, 2, 1)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.email_verified = True
    user.created_at = datetime(2026, 1, 1)
    user.updated_at = datetime(2026, 2, 1)
    return user


@pytest.fixture
def mock_admin_user():
    """建立模擬管理員"""
    from app.extended.models import User

    user = MagicMock(spec=User)
    user.id = 2
    user.email = "admin@example.com"
    user.username = "admin"
    user.is_active = True
    user.is_admin = True
    user.is_superuser = False
    user.role = "admin"
    user.permissions = '["documents:read", "documents:write", "admin:panel"]'
    return user


@pytest.fixture
def mock_superuser():
    """建立模擬超級管理員"""
    from app.extended.models import User

    user = MagicMock(spec=User)
    user.id = 3
    user.email = "super@example.com"
    user.username = "superadmin"
    user.is_active = True
    user.is_admin = True
    user.is_superuser = True
    user.role = "superadmin"
    user.permissions = None
    return user


# ============================================================
# 密碼驗證測試
# ============================================================

class TestVerifyPassword:
    """verify_password 方法測試"""

    def test_verify_password_correct(self):
        """測試正確密碼驗證"""
        from app.core.auth_service import AuthService

        hashed = AuthService.get_password_hash("my_secure_password")
        result = AuthService.verify_password("my_secure_password", hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """測試錯誤密碼驗證"""
        from app.core.auth_service import AuthService

        hashed = AuthService.get_password_hash("correct_password")
        result = AuthService.verify_password("wrong_password", hashed)
        assert result is False

    def test_verify_password_invalid_hash(self):
        """測試非法 hash 格式返回 False（不回退到明文比較）"""
        from app.core.auth_service import AuthService

        result = AuthService.verify_password("password", "not_a_valid_hash")
        assert result is False

    def test_get_password_hash_returns_bcrypt(self):
        """測試密碼 hash 使用 bcrypt 格式"""
        from app.core.auth_service import AuthService

        hashed = AuthService.get_password_hash("test_password")
        assert hashed.startswith("$2b$")


# ============================================================
# Token 建立與驗證測試
# ============================================================

class TestCreateAccessToken:
    """create_access_token 方法測試"""

    def test_create_access_token_default_expiry(self):
        """測試建立存取令牌使用預設過期時間"""
        from app.core.auth_service import AuthService

        token = AuthService.create_access_token(
            data={"sub": "1", "email": "test@example.com"}
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_custom_expiry(self):
        """測試建立存取令牌使用自訂過期時間"""
        from app.core.auth_service import AuthService

        token = AuthService.create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(hours=2)
        )
        assert isinstance(token, str)

    def test_create_access_token_with_jti(self):
        """測試建立存取令牌含自訂 JTI"""
        from app.core.auth_service import AuthService

        custom_jti = "custom-jti-12345"
        token = AuthService.create_access_token(
            data={"sub": "1"},
            jti=custom_jti
        )

        payload = AuthService.verify_token(token)
        assert payload is not None
        assert payload["jti"] == custom_jti


class TestCreateRefreshToken:
    """create_refresh_token 方法測試"""

    def test_create_refresh_token(self):
        """測試建立刷新令牌"""
        from app.core.auth_service import AuthService

        token = AuthService.create_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_refresh_token_uniqueness(self):
        """測試刷新令牌每次不同"""
        from app.core.auth_service import AuthService

        token1 = AuthService.create_refresh_token()
        token2 = AuthService.create_refresh_token()
        assert token1 != token2


class TestVerifyToken:
    """verify_token 方法測試"""

    def test_verify_token_valid(self):
        """測試驗證有效令牌"""
        from app.core.auth_service import AuthService

        token = AuthService.create_access_token(
            data={"sub": "42", "email": "user@example.com"}
        )

        payload = AuthService.verify_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "user@example.com"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_verify_token_expired(self):
        """測試驗證過期令牌回傳 None"""
        from app.core.auth_service import AuthService

        token = AuthService.create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-1)  # 已過期
        )

        payload = AuthService.verify_token(token)
        assert payload is None

    def test_verify_token_invalid(self):
        """測試驗證無效令牌回傳 None"""
        from app.core.auth_service import AuthService

        payload = AuthService.verify_token("invalid.token.string")
        assert payload is None

    def test_verify_token_tampered(self):
        """測試驗證被竄改的令牌回傳 None"""
        from app.core.auth_service import AuthService

        token = AuthService.create_access_token(data={"sub": "1"})
        # 竄改最後幾個字元
        tampered = token[:-5] + "XXXXX"

        payload = AuthService.verify_token(tampered)
        assert payload is None


# ============================================================
# Cookie 管理測試
# ============================================================

class TestSetAuthCookies:
    """set_auth_cookies 方法測試"""

    def test_set_auth_cookies(self):
        """測試設定認證 cookies"""
        from app.core.auth_service import AuthService
        from app.schemas.auth import TokenResponse, UserResponse

        mock_response = MagicMock()

        # 建立 mock token data
        mock_user_info = MagicMock(spec=UserResponse)
        token_data = MagicMock(spec=TokenResponse)
        token_data.access_token = "test_access_token"
        token_data.refresh_token = "test_refresh_token"
        token_data.expires_in = 1800
        token_data.user_info = mock_user_info

        with patch("app.core.auth_service.generate_csrf_token", return_value="csrf_123"), \
             patch("app.core.auth_service.set_csrf_cookie"), \
             patch("app.core.auth_service.settings") as mock_settings:
            mock_settings.DEVELOPMENT_MODE = True

            AuthService.set_auth_cookies(mock_response, token_data)

        # 驗證 set_cookie 被呼叫（access_token + refresh_token）
        assert mock_response.set_cookie.call_count >= 2

        # 驗證 access_token cookie 參數
        access_call = mock_response.set_cookie.call_args_list[0]
        assert access_call.kwargs["key"] == "access_token"
        assert access_call.kwargs["httponly"] is True
        assert access_call.kwargs["samesite"] == "lax"

    def test_clear_auth_cookies(self):
        """測試清除認證 cookies"""
        from app.core.auth_service import AuthService

        mock_response = MagicMock()

        with patch("app.core.csrf.clear_csrf_cookie"):
            AuthService.clear_auth_cookies(mock_response)

        # 驗證 delete_cookie 被呼叫
        assert mock_response.delete_cookie.call_count >= 2


# ============================================================
# Session 管理測試
# ============================================================

class TestRevokeSession:
    """revoke_session 方法測試"""

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, mock_db):
        """測試成功撤銷 session"""
        from app.core.auth_service import AuthService

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = await AuthService.revoke_session(mock_db, "test-jti-123")

        assert result is True
        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(self, mock_db):
        """測試撤銷不存在的 session 返回 False"""
        from app.core.auth_service import AuthService

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        result = await AuthService.revoke_session(mock_db, "nonexistent-jti")

        assert result is False


# ============================================================
# 權限檢查測試
# ============================================================

class TestCheckPermission:
    """check_permission 方法測試"""

    def test_check_permission_superuser_always_true(self, mock_superuser):
        """測試超級管理員總是有權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_permission(mock_superuser, "any:permission")
        assert result is True

    def test_check_permission_has_permission(self, mock_user):
        """測試使用者擁有指定權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_permission(mock_user, "documents:read")
        assert result is True

    def test_check_permission_lacks_permission(self, mock_user):
        """測試使用者缺少指定權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_permission(mock_user, "admin:panel")
        assert result is False

    def test_check_permission_no_permissions(self):
        """測試使用者無任何權限"""
        from app.core.auth_service import AuthService
        from app.extended.models import User

        user = MagicMock(spec=User)
        user.is_superuser = False
        user.permissions = None

        result = AuthService.check_permission(user, "documents:read")
        assert result is False

    def test_check_permission_invalid_json(self):
        """測試權限欄位為無效 JSON"""
        from app.core.auth_service import AuthService
        from app.extended.models import User

        user = MagicMock(spec=User)
        user.is_superuser = False
        user.permissions = "not_valid_json"

        result = AuthService.check_permission(user, "documents:read")
        assert result is False


class TestCheckAdminPermission:
    """check_admin_permission 方法測試"""

    def test_check_admin_permission_admin(self, mock_admin_user):
        """測試管理員有管理權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_admin_permission(mock_admin_user)
        assert result is True

    def test_check_admin_permission_superuser(self, mock_superuser):
        """測試超級管理員有管理權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_admin_permission(mock_superuser)
        assert result is True

    def test_check_admin_permission_regular_user(self, mock_user):
        """測試一般使用者無管理權限"""
        from app.core.auth_service import AuthService

        result = AuthService.check_admin_permission(mock_user)
        assert result is False


# ============================================================
# 網域白名單測試
# ============================================================

class TestCheckEmailDomain:
    """check_email_domain 方法測試"""

    def test_check_email_domain_allowed(self):
        """測試允許的網域"""
        from app.core.auth_service import AuthService

        with patch("app.core.auth_service.settings") as mock_settings:
            mock_settings.GOOGLE_ALLOWED_DOMAINS = "example.com,corp.com"

            result = AuthService.check_email_domain("user@example.com")
            assert result is True

    def test_check_email_domain_not_allowed(self):
        """測試不允許的網域"""
        from app.core.auth_service import AuthService

        with patch("app.core.auth_service.settings") as mock_settings:
            mock_settings.GOOGLE_ALLOWED_DOMAINS = "example.com,corp.com"

            result = AuthService.check_email_domain("user@unknown.com")
            assert result is False

    def test_check_email_domain_no_whitelist(self):
        """測試未設定白名單時允許所有"""
        from app.core.auth_service import AuthService

        with patch("app.core.auth_service.settings") as mock_settings:
            mock_settings.GOOGLE_ALLOWED_DOMAINS = ""

            result = AuthService.check_email_domain("user@anything.com")
            assert result is True


# ============================================================
# Token JTI 測試
# ============================================================

class TestGenerateTokenJti:
    """generate_token_jti 方法測試"""

    def test_generate_token_jti_uniqueness(self):
        """測試 JTI 唯一性"""
        from app.core.auth_service import AuthService

        jti1 = AuthService.generate_token_jti()
        jti2 = AuthService.generate_token_jti()

        assert jti1 != jti2
        assert isinstance(jti1, str)
        assert len(jti1) == 36  # UUID 格式


# ============================================================
# 密碼強度驗證測試
# ============================================================

class TestValidatePasswordStrength:
    """validate_password_strength 方法測試"""

    def test_validate_password_strength_valid(self):
        """測試強密碼驗證通過"""
        from app.core.auth_service import AuthService

        # 12+ 字元 + 大小寫 + 數字 + 特殊字元
        is_valid, message = AuthService.validate_password_strength(
            "MyStr0ng!Pass99"
        )
        assert is_valid is True

    def test_validate_password_strength_too_short(self):
        """測試短密碼驗證失敗"""
        from app.core.auth_service import AuthService

        is_valid, message = AuthService.validate_password_strength("Short1!")
        assert is_valid is False

    def test_validate_password_strength_raise_on_invalid(self):
        """測試 raise_on_invalid 模式"""
        from app.core.auth_service import AuthService

        with pytest.raises(ValueError):
            AuthService.validate_password_strength(
                "weak", raise_on_invalid=True
            )
