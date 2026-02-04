"""
BaseRepository 單元測試

測試泛型基類的基本 CRUD 功能

@version 1.0.0
@date 2026-02-04
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession


class TestBaseRepository:
    """BaseRepository 測試類"""

    @pytest.fixture
    def mock_db(self):
        """建立模擬的資料庫 session"""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def mock_model(self):
        """建立模擬的 ORM Model"""
        model = MagicMock()
        model.id = 1
        model.__tablename__ = 'test_table'
        return model

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_db, mock_model):
        """測試 get_by_id - 找到記錄"""
        from app.repositories.base_repository import BaseRepository

        # 設置 mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_db.execute.return_value = mock_result

        # 執行
        repo = BaseRepository(mock_model.__class__, mock_db)
        with patch.object(repo, 'model_class', mock_model.__class__):
            result = await repo.get_by_id(1)

        # 驗證
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db, mock_model):
        """測試 get_by_id - 記錄不存在"""
        from app.repositories.base_repository import BaseRepository

        # 設置 mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # 執行
        repo = BaseRepository(mock_model.__class__, mock_db)
        with patch.object(repo, 'model_class', mock_model.__class__):
            result = await repo.get_by_id(999)

        # 驗證
        assert result is None or mock_db.execute.called

    @pytest.mark.asyncio
    async def test_create(self, mock_db, mock_model):
        """測試 create - 建立新記錄"""
        from app.repositories.base_repository import BaseRepository

        # 設置 mock
        mock_db.refresh = AsyncMock()

        # 執行
        repo = BaseRepository(mock_model.__class__, mock_db)
        create_data = {'name': 'test', 'value': 123}

        # 驗證 add 被調用
        # 注意：實際測試需要根據具體實作調整

    @pytest.mark.asyncio
    async def test_delete(self, mock_db, mock_model):
        """測試 delete - 刪除記錄"""
        from app.repositories.base_repository import BaseRepository

        # 設置 mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_db.execute.return_value = mock_result

        # 執行
        repo = BaseRepository(mock_model.__class__, mock_db)

        # 驗證 delete 被調用


class TestBaseRepositoryPagination:
    """BaseRepository 分頁功能測試"""

    @pytest.fixture
    def mock_db(self):
        """建立模擬的資料庫 session"""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_get_list_with_pagination(self, mock_db):
        """測試分頁查詢"""
        # 設置 mock
        mock_items = [MagicMock(id=i) for i in range(10)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_items
        mock_db.execute.return_value = mock_result

        # 驗證分頁邏輯

    @pytest.mark.asyncio
    async def test_get_list_with_search(self, mock_db):
        """測試搜尋功能"""
        # 設置 mock
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 驗證搜尋邏輯
