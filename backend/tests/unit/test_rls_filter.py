# -*- coding: utf-8 -*-
"""
RLSFilter 單元測試

測試統一的 Row-Level Security 過濾邏輯。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from app.core.rls_filter import RLSFilter


class TestRLSFilter:
    """RLSFilter 類別測試"""

    def test_get_user_rls_flags_with_admin(self):
        """測試管理員的 RLS 標誌"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = True
        mock_user.is_superuser = False

        user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(mock_user)

        assert user_id == 1
        assert is_admin is True
        assert is_superuser is False

    def test_get_user_rls_flags_with_superuser(self):
        """測試超級使用者的 RLS 標誌"""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.is_admin = False
        mock_user.is_superuser = True

        user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(mock_user)

        assert user_id == 2
        assert is_admin is False
        assert is_superuser is True

    def test_get_user_rls_flags_with_regular_user(self):
        """測試一般使用者的 RLS 標誌"""
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.is_admin = False
        mock_user.is_superuser = False

        user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(mock_user)

        assert user_id == 3
        assert is_admin is False
        assert is_superuser is False

    def test_get_user_rls_flags_with_none(self):
        """測試 None 使用者的 RLS 標誌"""
        user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(None)

        assert user_id is None
        assert is_admin is False
        assert is_superuser is False

    def test_is_user_admin_with_admin(self):
        """測試 is_user_admin 對管理員"""
        mock_user = MagicMock()
        mock_user.is_admin = True
        mock_user.is_superuser = False

        assert RLSFilter.is_user_admin(mock_user) is True

    def test_is_user_admin_with_superuser(self):
        """測試 is_user_admin 對超級使用者"""
        mock_user = MagicMock()
        mock_user.is_admin = False
        mock_user.is_superuser = True

        assert RLSFilter.is_user_admin(mock_user) is True

    def test_is_user_admin_with_regular_user(self):
        """測試 is_user_admin 對一般使用者"""
        mock_user = MagicMock()
        mock_user.is_admin = False
        mock_user.is_superuser = False

        assert RLSFilter.is_user_admin(mock_user) is False

    def test_is_user_admin_with_none(self):
        """測試 is_user_admin 對 None"""
        assert RLSFilter.is_user_admin(None) is False

    def test_get_user_accessible_project_ids(self):
        """測試取得使用者可存取的專案 ID 子查詢"""
        user_id = 123
        query = RLSFilter.get_user_accessible_project_ids(user_id)

        # 確認回傳的是 SQLAlchemy Select 物件
        assert query is not None
        # 確認查詢包含正確的 user_id 條件
        query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "user_id" in query_str
        assert "status" in query_str

    def test_active_assignment_statuses(self):
        """測試有效的專案狀態常數"""
        assert 'active' in RLSFilter.ACTIVE_ASSIGNMENT_STATUSES
        assert 'Active' in RLSFilter.ACTIVE_ASSIGNMENT_STATUSES
        assert None in RLSFilter.ACTIVE_ASSIGNMENT_STATUSES


class TestRLSFilterApplyDocument:
    """測試 apply_document_rls 方法"""

    def test_admin_skips_filter(self):
        """測試管理員跳過 RLS 過濾"""
        mock_query = MagicMock()
        mock_document = MagicMock()

        result = RLSFilter.apply_document_rls(
            mock_query, mock_document, user_id=1, is_admin=True, is_superuser=False
        )

        # 管理員不應套用過濾，回傳原始查詢
        assert result == mock_query
        mock_query.where.assert_not_called()

    def test_superuser_skips_filter(self):
        """測試超級使用者跳過 RLS 過濾"""
        mock_query = MagicMock()
        mock_document = MagicMock()

        result = RLSFilter.apply_document_rls(
            mock_query, mock_document, user_id=1, is_admin=False, is_superuser=True
        )

        # 超級使用者不應套用過濾
        assert result == mock_query
        mock_query.where.assert_not_called()


class TestRLSFilterApplyProject:
    """測試 apply_project_rls 方法"""

    def test_admin_skips_filter(self):
        """測試管理員跳過專案 RLS 過濾"""
        mock_query = MagicMock()
        mock_project = MagicMock()

        result = RLSFilter.apply_project_rls(
            mock_query, mock_project, user_id=1, is_admin=True, is_superuser=False
        )

        assert result == mock_query
        mock_query.where.assert_not_called()

    def test_superuser_skips_filter(self):
        """測試超級使用者跳過專案 RLS 過濾"""
        mock_query = MagicMock()
        mock_project = MagicMock()

        result = RLSFilter.apply_project_rls(
            mock_query, mock_project, user_id=1, is_admin=False, is_superuser=True
        )

        assert result == mock_query
        mock_query.where.assert_not_called()


class TestRLSFilterRoleFallback:
    """P-12 (2026-05-06)：role 欄位 fallback 鎖定。

    事故：李昭德 id=19 DB 實況 role='admin' 但 is_admin=False，
    走原 RLS 邏輯被當一般使用者，看不到參與專案的 document。
    修法：is_user_admin / get_user_rls_flags 同時看 role 欄位。
    """

    def test_is_user_admin_role_admin_with_false_flag(self):
        """role='admin' 但 is_admin=False 仍應視為管理員（資料對齊前的相容防線）"""
        from unittest.mock import MagicMock
        u = MagicMock()
        u.is_admin = False
        u.is_superuser = False
        u.role = 'admin'
        assert RLSFilter.is_user_admin(u) is True

    def test_is_user_admin_role_superuser_with_false_flag(self):
        """role='superuser' 但 is_superuser=False 仍應視為超級使用者"""
        from unittest.mock import MagicMock
        u = MagicMock()
        u.is_admin = False
        u.is_superuser = False
        u.role = 'superuser'
        assert RLSFilter.is_user_admin(u) is True

    def test_is_user_admin_role_normal(self):
        """role='user' / 'staff' 等非管理員角色應為 False"""
        from unittest.mock import MagicMock
        for role in ('user', 'staff', '', None):
            u = MagicMock()
            u.is_admin = False
            u.is_superuser = False
            u.role = role
            assert RLSFilter.is_user_admin(u) is False, f"role={role!r} 不應視為 admin"

    def test_get_user_rls_flags_role_fallback(self):
        """get_user_rls_flags 對 role='admin' 應將 is_admin 推導為 True"""
        from unittest.mock import MagicMock
        u = MagicMock()
        u.id = 19
        u.is_admin = False
        u.is_superuser = False
        u.role = 'admin'
        user_id, is_admin, is_superuser = RLSFilter.get_user_rls_flags(u)
        assert user_id == 19
        assert is_admin is True
        assert is_superuser is False  # role='admin' 不該升為 superuser

    def test_get_user_rls_flags_role_superuser(self):
        """role='superuser' 應同時推導 is_admin + is_superuser"""
        from unittest.mock import MagicMock
        u = MagicMock()
        u.id = 13
        u.is_admin = False
        u.is_superuser = False
        u.role = 'superuser'
        _, is_admin, is_superuser = RLSFilter.get_user_rls_flags(u)
        assert is_admin is True
        assert is_superuser is True


class TestRLSFilterAliasGroupExpansion:
    """TaskB (2026-05-06)：RLS 自動展開 alias group。

    場景：未合併或已合併的同人多帳號（如李昭德 id=11 hotmail / id=19 gmail），
    任一帳號登入應吃到整組 alias 的 project_user_assignments。

    本測試只驗 SQL 結構（subquery 含 COALESCE / 雙向 OR），實際 DB 驗證見
    integration test。
    """

    def test_get_alias_group_subquery_uses_coalesce_and_or(self):
        """alias group subquery 應有 COALESCE(canonical_user_id, id) + 雙向 OR"""
        sub = RLSFilter.get_alias_group_subquery(user_id=19)
        sql = str(sub.compile(compile_kwargs={"literal_binds": True}))
        # COALESCE 解析 root_id
        assert "coalesce" in sql.lower(), f"alias subquery 應含 COALESCE: {sql}"
        # 雙向：id == root OR canonical_user_id == root
        assert sql.lower().count("user.id =") + sql.lower().count("users.id =") >= 1
        assert "canonical_user_id" in sql.lower()

    def test_get_user_accessible_project_ids_uses_alias_group(self):
        """get_user_accessible_project_ids 應透過 alias group 子查詢過濾"""
        sub = RLSFilter.get_user_accessible_project_ids(user_id=19)
        sql = str(sub.compile(compile_kwargs={"literal_binds": True}))
        # 應透過 user_id IN (alias subquery)，而非 user_id = literal
        assert " in (" in sql.lower(), f"應使用 IN subquery 展開 alias: {sql}"
        assert "canonical_user_id" in sql.lower(), \
            f"應展開 alias group（subquery 含 canonical_user_id）: {sql}"

    def test_apply_project_rls_uses_alias_group(self):
        """apply_project_rls 對非 admin 使用者應用 alias group 子查詢"""
        from sqlalchemy import select as sa_select
        from app.extended.models import ContractProject

        base = sa_select(ContractProject)
        result = RLSFilter.apply_project_rls(
            base, ContractProject, user_id=19, is_admin=False, is_superuser=False
        )
        sql = str(result.compile(compile_kwargs={"literal_binds": True}))
        # exists subquery 內 user_id IN (alias group)
        assert "canonical_user_id" in sql.lower(), \
            f"apply_project_rls 應展開 alias group: {sql[:500]}"
