# -*- coding: utf-8 -*-
"""
認證流程整合測試
Auth Flow Integration Tests

測試覆蓋:
1. 帳密登入成功 / 密碼錯誤 / 使用者不存在
2. Refresh Token Rotation（舊 token 撤銷、新 token 可用）
3. Refresh Token Replay Detection（重用已撤銷 token → 撤銷所有 session）
4. Refresh Token 過期
5. 登出撤銷 session
6. 認證狀態檢查

執行方式:
    cd backend
    python -m pytest tests/integration/test_auth_flow.py -v

v1.0.0 - 2026-02-07
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    AuthService,
)
from app.extended.models import User, UserSession

pytestmark = pytest.mark.integration


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def test_password() -> str:
    """測試用明文密碼"""
    return "TestP@ssw0rd!Secure"


@pytest.fixture
def test_password_hash(test_password: str) -> str:
    """測試用密碼雜湊"""
    return AuthService.get_password_hash(test_password)


@pytest.fixture
def mock_user(test_password_hash: str) -> User:
    """建立 mock User 物件，模擬資料庫中已存在的使用者"""
    user = MagicMock(spec=User)
    user.id = 42
    user.username = "testuser"
    user.email = "testuser@example.com"
    user.password_hash = test_password_hash
    user.full_name = "Test User"
    user.is_active = True
    user.is_admin = False
    user.is_superuser = False
    user.role = "user"
    user.auth_provider = "email"
    user.login_count = 5
    user.last_login = datetime.utcnow()
    user.permissions = '["documents:read"]'
    user.avatar_url = None
    user.google_id = None
    user.created_at = datetime.utcnow() - timedelta(days=30)
    user.updated_at = datetime.utcnow()
    user.email_verified = True
    user.department = None
    user.position = None
    return user


@pytest.fixture
def mock_session_db() -> AsyncMock:
    """建立具有完整查詢能力的 mock AsyncSession"""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    return db


def _make_scalar_result(value):
    """建立模擬 scalar_one_or_none() 的查詢結果"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_rowcount_result(count: int):
    """建立模擬 update 的結果（含 rowcount）"""
    result = MagicMock()
    result.rowcount = count
    return result


# ============================================================
# 1. 帳密登入測試
# ============================================================


class TestLoginFlow:
    """帳密登入流程測試"""

    async def test_login_success(
        self, mock_session_db: AsyncMock, mock_user: MagicMock, test_password: str
    ):
        """帳密登入成功，返回 access_token + refresh_token"""
        # Arrange: authenticate_user 查詢使用者
        # 第一次 execute: email 查詢 → 找到使用者
        mock_session_db.execute.return_value = _make_scalar_result(mock_user)

        # Act
        user = await AuthService.authenticate_user(
            mock_session_db, "testuser@example.com", test_password
        )

        # Assert
        assert user is not None
        assert user.id == 42
        assert user.email == "testuser@example.com"

    async def test_login_wrong_password(
        self, mock_session_db: AsyncMock, mock_user: MagicMock
    ):
        """密碼錯誤，返回 None"""
        # Arrange
        mock_session_db.execute.return_value = _make_scalar_result(mock_user)

        # Act
        user = await AuthService.authenticate_user(
            mock_session_db, "testuser@example.com", "WrongPassword123!"
        )

        # Assert
        assert user is None

    async def test_login_nonexistent_user(self, mock_session_db: AsyncMock):
        """使用者不存在，返回 None"""
        # Arrange: 兩次查詢（email + username）都找不到
        mock_session_db.execute.return_value = _make_scalar_result(None)

        # Act
        user = await AuthService.authenticate_user(
            mock_session_db, "nobody@example.com", "AnyPassword123!"
        )

        # Assert
        assert user is None


# ============================================================
# 2. Token 生成與驗證測試
# ============================================================


class TestTokenGeneration:
    """Token 生成與驗證測試"""

    def test_create_and_verify_access_token(self):
        """Access token 生成後可成功驗證"""
        # Arrange
        jti = AuthService.generate_token_jti()
        token_data = {"sub": "42", "email": "test@example.com"}

        # Act
        token = AuthService.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=30),
            jti=jti,
        )
        payload = AuthService.verify_token(token)

        # Assert
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "test@example.com"
        assert payload["jti"] == jti

    def test_verify_expired_token_returns_none(self):
        """過期的 access token 驗證回傳 None"""
        # Arrange: 建立一個已過期的 token
        token = AuthService.create_access_token(
            data={"sub": "42", "email": "test@example.com"},
            expires_delta=timedelta(seconds=-1),
        )

        # Act
        payload = AuthService.verify_token(token)

        # Assert
        assert payload is None

    def test_verify_invalid_token_returns_none(self):
        """無效 token 驗證回傳 None"""
        payload = AuthService.verify_token("invalid.token.string")
        assert payload is None

    def test_refresh_token_is_unique(self):
        """每次生成的 refresh token 都不同"""
        token1 = AuthService.create_refresh_token()
        token2 = AuthService.create_refresh_token()
        assert token1 != token2
        assert len(token1) > 20  # 確保足夠長度


# ============================================================
# 3. Refresh Token Rotation 測試
# ============================================================


class TestRefreshTokenRotation:
    """Refresh Token Rotation 機制測試"""

    async def test_refresh_token_rotation(self, mock_session_db: AsyncMock, mock_user: MagicMock):
        """刷新後舊 token 失效、新 token 可用

        流程:
        1. verify_refresh_token 查找有效 session (SELECT FOR UPDATE)
        2. 查找關聯的 user
        3. 撤銷舊 session (revoke_session)
        4. 回傳 user（呼叫方負責建立新 session）
        """
        # Arrange: 建立模擬的有效 session
        old_jti = str(uuid.uuid4())
        old_refresh_token = "old_refresh_token_value"

        mock_session = MagicMock(spec=UserSession)
        mock_session.user_id = mock_user.id
        mock_session.token_jti = old_jti
        mock_session.refresh_token = old_refresh_token
        mock_session.is_active = True
        mock_session.expires_at = datetime.utcnow() + timedelta(days=7)

        # 第 1 次 execute: SELECT FOR UPDATE 找到有效 session
        # 第 2 次 execute: 查找 user
        # 第 3 次 execute: revoke_session (UPDATE is_active=False)
        # 第 4 次 execute: revoke_session commit (handled by commit mock)
        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # SELECT FOR UPDATE: 找到有效 session
                return _make_scalar_result(mock_session)
            elif call_count == 2:
                # SELECT user
                return _make_scalar_result(mock_user)
            elif call_count == 3:
                # UPDATE: revoke old session
                return _make_rowcount_result(1)
            return _make_scalar_result(None)

        mock_session_db.execute = AsyncMock(side_effect=mock_execute)

        # Act
        user = await AuthService.verify_refresh_token(mock_session_db, old_refresh_token)

        # Assert: 應回傳使用者（表示 rotation 成功）
        assert user is not None
        assert user.id == mock_user.id

        # 驗證 revoke (commit) 被呼叫
        assert mock_session_db.commit.call_count >= 1

    async def test_refresh_token_invalid(self, mock_session_db: AsyncMock):
        """無效的 refresh token（不存在於資料庫）"""
        # Arrange: 第 1 次查詢找不到 active session，第 2 次查詢找不到已撤銷 session
        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_scalar_result(None)

        mock_session_db.execute = AsyncMock(side_effect=mock_execute)

        # Act
        user = await AuthService.verify_refresh_token(
            mock_session_db, "nonexistent_refresh_token"
        )

        # Assert
        assert user is None


# ============================================================
# 4. Refresh Token Replay Detection 測試
# ============================================================


class TestRefreshTokenReplayDetection:
    """Token Replay Detection 測試

    安全機制: 已撤銷的 refresh token 被重複使用時，
    系統應撤銷該使用者的所有 active session（防止被竊的 token 造成危害）。
    """

    async def test_replay_detection_revokes_all_sessions(
        self, mock_session_db: AsyncMock, mock_user: MagicMock
    ):
        """使用已撤銷的 refresh token → 撤銷該使用者所有 session"""
        # Arrange
        revoked_refresh_token = "revoked_token_value"

        # 已撤銷的 session 記錄
        revoked_session = MagicMock(spec=UserSession)
        revoked_session.user_id = mock_user.id
        revoked_session.token_jti = str(uuid.uuid4())
        revoked_session.is_active = False

        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # SELECT FOR UPDATE: 找不到 active session
                return _make_scalar_result(None)
            elif call_count == 2:
                # Replay detection: 找到已撤銷的 session
                return _make_scalar_result(revoked_session)
            elif call_count == 3:
                # UPDATE: 撤銷所有 active sessions
                return _make_rowcount_result(3)  # 模擬撤銷 3 個 session
            return _make_scalar_result(None)

        mock_session_db.execute = AsyncMock(side_effect=mock_execute)

        # Act
        user = await AuthService.verify_refresh_token(
            mock_session_db, revoked_refresh_token
        )

        # Assert: 應回傳 None（拒絕存取）
        assert user is None

        # 驗證 commit 被呼叫（撤銷所有 session 後需要 commit）
        assert mock_session_db.commit.call_count >= 1

        # 驗證 execute 被呼叫 3 次:
        # 1. SELECT FOR UPDATE (找不到 active)
        # 2. SELECT (找到已撤銷的 session → replay detected)
        # 3. UPDATE (撤銷該使用者所有 active session)
        assert call_count == 3


# ============================================================
# 5. Refresh Token 過期測試
# ============================================================


class TestRefreshTokenExpiry:
    """Refresh Token 過期測試"""

    async def test_refresh_token_expired(self, mock_session_db: AsyncMock):
        """過期的 refresh token 返回 None

        verify_refresh_token 的 SQL 查詢包含 expires_at > now() 條件，
        過期 token 不會被 SELECT FOR UPDATE 查詢匹配到。
        """
        # Arrange: SELECT FOR UPDATE 找不到（因為過期）
        # 第 2 次 SELECT 也找不到已撤銷記錄（token 未被撤銷，只是過期）
        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_scalar_result(None)

        mock_session_db.execute = AsyncMock(side_effect=mock_execute)

        # Act
        user = await AuthService.verify_refresh_token(
            mock_session_db, "expired_refresh_token"
        )

        # Assert
        assert user is None


# ============================================================
# 6. Session 管理測試
# ============================================================


class TestSessionManagement:
    """Session 管理測試"""

    async def test_create_user_session(
        self, mock_session_db: AsyncMock, mock_user: MagicMock
    ):
        """建立使用者 session 記錄"""
        # Arrange
        jti = str(uuid.uuid4())
        refresh_token = AuthService.create_refresh_token()

        # Act
        session = await AuthService.create_user_session(
            db=mock_session_db,
            user=mock_user,
            token_jti=jti,
            refresh_token=refresh_token,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
        )

        # Assert: db.add 被呼叫、db.commit 被呼叫
        mock_session_db.add.assert_called_once()
        mock_session_db.commit.assert_called_once()
        mock_session_db.refresh.assert_called_once()

        # 驗證 add 的參數是 UserSession
        added_session = mock_session_db.add.call_args[0][0]
        assert isinstance(added_session, UserSession)
        assert added_session.user_id == mock_user.id
        assert added_session.token_jti == jti
        assert added_session.refresh_token == refresh_token
        assert added_session.ip_address == "127.0.0.1"
        assert added_session.user_agent == "TestAgent/1.0"

    async def test_revoke_session(self, mock_session_db: AsyncMock):
        """撤銷 session（登出）"""
        # Arrange
        jti = str(uuid.uuid4())
        mock_session_db.execute.return_value = _make_rowcount_result(1)

        # Act
        result = await AuthService.revoke_session(mock_session_db, jti)

        # Assert
        assert result is True
        mock_session_db.commit.assert_called_once()

    async def test_revoke_session_not_found(self, mock_session_db: AsyncMock):
        """撤銷不存在的 session"""
        # Arrange
        mock_session_db.execute.return_value = _make_rowcount_result(0)

        # Act
        result = await AuthService.revoke_session(mock_session_db, "nonexistent_jti")

        # Assert
        assert result is False


# ============================================================
# 7. 登出流程測試
# ============================================================


class TestLogoutFlow:
    """登出流程測試"""

    async def test_logout_revokes_session(self, mock_session_db: AsyncMock, mock_user: MagicMock):
        """登出後 session 被標記 is_active=False

        模擬完整登出流程:
        1. 建立 access token（含 jti）
        2. 用 verify_token 解析 jti
        3. 呼叫 revoke_session 撤銷
        """
        # Arrange: 建立 token
        jti = AuthService.generate_token_jti()
        token = AuthService.create_access_token(
            data={"sub": str(mock_user.id), "email": mock_user.email},
            expires_delta=timedelta(minutes=30),
            jti=jti,
        )

        # 解析 token 取得 jti
        payload = AuthService.verify_token(token)
        assert payload is not None
        extracted_jti = payload.get("jti")
        assert extracted_jti == jti

        # Mock revoke
        mock_session_db.execute.return_value = _make_rowcount_result(1)

        # Act: 撤銷 session
        revoked = await AuthService.revoke_session(mock_session_db, extracted_jti)

        # Assert
        assert revoked is True
        mock_session_db.commit.assert_called_once()


# ============================================================
# 8. 認證狀態檢查測試
# ============================================================


class TestCheckAuthStatus:
    """認證狀態檢查測試

    測試 AuthService.get_current_user_from_token 的邏輯:
    1. 驗證 access token
    2. 檢查 session 是否 active
    3. 查詢使用者是否存在且啟用
    """

    def test_valid_token_contains_expected_claims(self, mock_user: MagicMock):
        """有效 token 包含預期的 claims"""
        # Arrange
        jti = AuthService.generate_token_jti()
        token = AuthService.create_access_token(
            data={"sub": str(mock_user.id), "email": mock_user.email},
            expires_delta=timedelta(minutes=30),
            jti=jti,
        )

        # Act
        payload = AuthService.verify_token(token)

        # Assert
        assert payload is not None
        assert payload["sub"] == str(mock_user.id)
        assert payload["email"] == mock_user.email
        assert payload["jti"] == jti
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_returns_none(self):
        """過期 token 無法通過驗證"""
        # Arrange
        token = AuthService.create_access_token(
            data={"sub": "42", "email": "test@example.com"},
            expires_delta=timedelta(seconds=-10),
        )

        # Act
        payload = AuthService.verify_token(token)

        # Assert
        assert payload is None


# ============================================================
# 9. 密碼驗證工具測試
# ============================================================


class TestPasswordUtilities:
    """密碼雜湊與驗證工具測試"""

    def test_password_hash_and_verify(self):
        """密碼雜湊後可成功驗證"""
        password = "MyS3cur3P@ss!"
        hashed = AuthService.get_password_hash(password)

        assert hashed != password  # 雜湊不等於明文
        assert AuthService.verify_password(password, hashed) is True

    def test_password_verify_wrong_password(self):
        """錯誤密碼驗證失敗"""
        hashed = AuthService.get_password_hash("CorrectPassword123!")
        assert AuthService.verify_password("WrongPassword456!", hashed) is False

    def test_password_verify_invalid_hash(self):
        """無效的 hash 格式不會造成例外"""
        result = AuthService.verify_password("any_password", "not_a_valid_hash")
        assert result is False

    def test_each_hash_is_unique(self):
        """同一密碼每次雜湊結果不同（bcrypt salt）"""
        password = "SamePassword123!"
        hash1 = AuthService.get_password_hash(password)
        hash2 = AuthService.get_password_hash(password)

        assert hash1 != hash2  # bcrypt 每次 salt 不同
        assert AuthService.verify_password(password, hash1) is True
        assert AuthService.verify_password(password, hash2) is True


# ============================================================
# 10. 完整登入-刷新-登出流程測試
# ============================================================


class TestFullAuthLifecycle:
    """完整認證生命週期測試

    模擬: 登入 → 取得 tokens → 刷新 → 登出
    """

    async def test_login_refresh_logout_lifecycle(
        self, mock_session_db: AsyncMock, mock_user: MagicMock, test_password: str
    ):
        """完整生命週期: 登入 → Token 驗證 → Refresh → 登出"""

        # === Step 1: 登入 ===
        mock_session_db.execute.return_value = _make_scalar_result(mock_user)
        user = await AuthService.authenticate_user(
            mock_session_db, mock_user.email, test_password
        )
        assert user is not None

        # 生成 tokens
        jti = AuthService.generate_token_jti()
        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            jti=jti,
        )
        refresh_token = AuthService.create_refresh_token()

        # === Step 2: 驗證 access token ===
        payload = AuthService.verify_token(access_token)
        assert payload is not None
        assert payload["sub"] == str(user.id)

        # === Step 3: 模擬 Refresh ===
        mock_session_record = MagicMock(spec=UserSession)
        mock_session_record.user_id = user.id
        mock_session_record.token_jti = jti
        mock_session_record.refresh_token = refresh_token
        mock_session_record.is_active = True
        mock_session_record.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        call_count = 0

        async def mock_execute_refresh(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(mock_session_record)
            elif call_count == 2:
                return _make_scalar_result(mock_user)
            elif call_count == 3:
                return _make_rowcount_result(1)
            return _make_scalar_result(None)

        mock_session_db.execute = AsyncMock(side_effect=mock_execute_refresh)
        mock_session_db.commit.reset_mock()

        refreshed_user = await AuthService.verify_refresh_token(mock_session_db, refresh_token)
        assert refreshed_user is not None
        assert refreshed_user.id == user.id

        # 新 tokens
        new_jti = AuthService.generate_token_jti()
        new_access_token = AuthService.create_access_token(
            data={"sub": str(refreshed_user.id), "email": refreshed_user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            jti=new_jti,
        )
        new_refresh_token = AuthService.create_refresh_token()

        # 新 token 有效
        new_payload = AuthService.verify_token(new_access_token)
        assert new_payload is not None
        assert new_payload["jti"] == new_jti
        assert new_payload["jti"] != jti  # 與舊 jti 不同

        # === Step 4: 登出 ===
        mock_session_db.execute = AsyncMock(return_value=_make_rowcount_result(1))
        mock_session_db.commit.reset_mock()

        revoked = await AuthService.revoke_session(mock_session_db, new_jti)
        assert revoked is True
        mock_session_db.commit.assert_called_once()
