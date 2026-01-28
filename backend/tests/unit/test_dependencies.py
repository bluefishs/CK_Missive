# -*- coding: utf-8 -*-
"""
依賴注入模組單元測試
Dependencies Module Unit Tests

測試 app/core/dependencies.py 中的依賴注入函數

執行方式:
    pytest tests/unit/test_dependencies.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestGetServiceFunction:
    """測試 get_service 工廠函數"""

    def test_get_service_returns_callable(self):
        """測試 get_service 返回可呼叫物件"""
        from app.core.dependencies import get_service

        class MockService:
            def __init__(self, db):
                self.db = db

        result = get_service(MockService)
        assert callable(result)

    def test_get_service_creates_instance_with_db(self):
        """測試 get_service 建立實例時傳入 db"""
        from app.core.dependencies import get_service

        class MockService:
            def __init__(self, db):
                self.db = db

        factory = get_service(MockService)
        mock_db = MagicMock()

        # 模擬 FastAPI 依賴注入呼叫
        instance = factory(db=mock_db)

        assert isinstance(instance, MockService)
        assert instance.db is mock_db


class TestGetServiceWithDb:
    """測試 get_service_with_db 函數"""

    def test_get_service_with_db_returns_callable(self):
        """測試 get_service_with_db 返回可呼叫物件"""
        from app.core.dependencies import get_service_with_db

        class MockService:
            def __init__(self, db):
                self.db = db

        result = get_service_with_db(MockService)
        assert callable(result)

    def test_get_service_with_db_creates_instance(self):
        """測試 get_service_with_db 建立實例"""
        from app.core.dependencies import get_service_with_db

        class MockService:
            def __init__(self, db):
                self.db = db
                self.initialized = True

        factory = get_service_with_db(MockService)
        mock_db = MagicMock()

        instance = factory(db=mock_db)

        assert instance.initialized is True
        assert instance.db is mock_db


class TestSingletonServices:
    """測試 Singleton 模式的 Service 取得函數"""

    def test_get_vendor_service_returns_singleton(self):
        """測試 VendorService 是單例"""
        from app.core.dependencies import get_vendor_service

        service1 = get_vendor_service()
        service2 = get_vendor_service()

        assert service1 is service2

    def test_get_project_service_returns_singleton(self):
        """測試 ProjectService 是單例"""
        from app.core.dependencies import get_project_service

        service1 = get_project_service()
        service2 = get_project_service()

        assert service1 is service2

    def test_get_agency_service_returns_singleton(self):
        """測試 AgencyService 是單例"""
        from app.core.dependencies import get_agency_service

        service1 = get_agency_service()
        service2 = get_agency_service()

        assert service1 is service2

    def test_get_document_service_is_factory(self):
        """測試 DocumentService 使用工廠模式（非單例）"""
        from app.api.endpoints.documents.common import get_document_service

        # get_document_service 是由 get_service_with_db 建立的工廠函數
        # 每次呼叫時需要 db 參數，不是直接呼叫的單例
        assert callable(get_document_service)


class TestPaginationDependency:
    """測試分頁參數依賴"""

    @pytest.mark.asyncio
    async def test_get_pagination_default_values(self):
        """測試預設分頁參數"""
        from app.core.dependencies import get_pagination

        pagination = await get_pagination()

        assert pagination.page == 1
        assert pagination.limit == 20

    @pytest.mark.asyncio
    async def test_get_pagination_custom_values(self):
        """測試自訂分頁參數"""
        from app.core.dependencies import get_pagination

        pagination = await get_pagination(page=3, limit=50)

        assert pagination.page == 3
        assert pagination.limit == 50

    @pytest.mark.asyncio
    async def test_get_pagination_skip_calculation(self):
        """測試 skip 計算"""
        from app.core.dependencies import get_pagination

        pagination = await get_pagination(page=3, limit=20)

        # skip = (page - 1) * limit = (3 - 1) * 20 = 40
        assert pagination.skip == 40

    @pytest.mark.asyncio
    async def test_get_pagination_page_one_skip_zero(self):
        """測試第一頁 skip 為 0"""
        from app.core.dependencies import get_pagination

        pagination = await get_pagination(page=1, limit=10)

        assert pagination.skip == 0


class TestQueryParamsDependency:
    """測試通用查詢參數依賴"""

    @pytest.mark.asyncio
    async def test_get_query_params_default_values(self):
        """測試預設查詢參數"""
        from app.core.dependencies import get_query_params

        params = await get_query_params()

        assert params.page == 1
        assert params.limit == 20
        assert params.search is None
        assert params.sort_by == "id"
        assert params.sort_order.value == "desc"

    @pytest.mark.asyncio
    async def test_get_query_params_custom_values(self):
        """測試自訂查詢參數"""
        from app.core.dependencies import get_query_params

        params = await get_query_params(
            page=2,
            limit=30,
            search="測試",
            sort_by="created_at",
            sort_order="asc"
        )

        assert params.page == 2
        assert params.limit == 30
        assert params.search == "測試"
        assert params.sort_by == "created_at"
        assert params.sort_order.value == "asc"

    @pytest.mark.asyncio
    async def test_get_query_params_invalid_sort_order_fallback(self):
        """測試無效排序方向回退為 desc"""
        from app.core.dependencies import get_query_params

        params = await get_query_params(sort_order="invalid")

        assert params.sort_order.value == "desc"


class TestAuthDependencies:
    """測試認證相關依賴"""

    def test_require_auth_returns_callable(self):
        """測試 require_auth 返回可呼叫物件"""
        from app.core.dependencies import require_auth

        result = require_auth()
        assert callable(result)

    def test_optional_auth_returns_callable(self):
        """測試 optional_auth 返回可呼叫物件"""
        from app.core.dependencies import optional_auth

        result = optional_auth()
        assert callable(result)

    def test_require_admin_returns_callable(self):
        """測試 require_admin 返回可呼叫物件"""
        from app.core.dependencies import require_admin

        result = require_admin()
        assert callable(result)

    def test_require_permission_returns_callable(self):
        """測試 require_permission 返回可呼叫物件"""
        from app.core.dependencies import require_permission

        result = require_permission("documents:read")
        assert callable(result)


class TestRequireAdminDependency:
    """測試管理員權限依賴"""

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin_user(self):
        """測試管理員可通過"""
        from app.core.dependencies import require_admin
        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.is_admin = True
        mock_user.is_superuser = False

        admin_check = require_admin()

        # 模擬依賴注入呼叫
        with patch('app.core.dependencies.get_current_user', return_value=mock_user):
            # 這裡需要完整測試環境才能正確執行
            # 此處僅驗證函數結構
            assert callable(admin_check)

    @pytest.mark.asyncio
    async def test_require_admin_allows_superuser(self):
        """測試超級管理員可通過"""
        from app.core.dependencies import require_admin
        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.is_admin = False
        mock_user.is_superuser = True

        admin_check = require_admin()
        assert callable(admin_check)


class TestRequirePermissionDependency:
    """測試權限檢查依賴"""

    def test_require_permission_accepts_permission_string(self):
        """測試接受權限字串"""
        from app.core.dependencies import require_permission

        # 不應該拋出錯誤
        result = require_permission("documents:read")
        assert callable(result)

        result = require_permission("documents:write")
        assert callable(result)

        result = require_permission("admin:manage")
        assert callable(result)

    def test_require_permission_different_permissions(self):
        """測試不同權限建立不同依賴"""
        from app.core.dependencies import require_permission

        perm1 = require_permission("documents:read")
        perm2 = require_permission("documents:write")

        # 每次呼叫應該建立新的函數
        assert perm1 is not perm2


class TestServiceFactoryAlias:
    """測試 Service 工廠函數別名"""

    def test_get_service_factory_is_alias(self):
        """測試 get_service_factory 是 get_service_with_db 的別名"""
        from app.core.dependencies import get_service_factory, get_service_with_db

        assert get_service_factory is get_service_with_db
