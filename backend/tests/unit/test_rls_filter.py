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
