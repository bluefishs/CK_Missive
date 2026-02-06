"""
BaseRepository 單元測試

測試泛型基類的基本 CRUD 功能。
使用真實 ORM Model 類別搭配 mock db session。

@version 2.0.0
@date 2026-02-06
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base_repository import BaseRepository
from app.extended.models import User


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
    def repo(self, mock_db):
        """建立使用 User model 的 BaseRepository"""
        return BaseRepository(mock_db, User)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db):
        """測試 get_by_id - 找到記錄"""
        mock_user = MagicMock(spec=User)
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(1)

        assert result == mock_user
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """測試 get_by_id - 記錄不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(999)

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_db):
        """測試 create - 建立新記錄"""
        mock_db.refresh = AsyncMock()

        create_data = {"username": "test", "email": "test@example.com"}
        result = await repo.create(create_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_found(self, repo, mock_db):
        """測試 delete - 成功刪除"""
        mock_user = MagicMock(spec=User)
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await repo.delete(1)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_user)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        """測試 delete - 記錄不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.delete(999)

        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_exists(self, repo, mock_db):
        """測試 exists - 記錄存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        result = await repo.exists(1)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self, repo, mock_db):
        """測試 exists - 記錄不存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.exists(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_count(self, repo, mock_db):
        """測試 count - 計算總數"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        result = await repo.count()

        assert result == 42


class TestBaseRepositorySearch:
    """BaseRepository 搜尋功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return BaseRepository(mock_db, User)

    @pytest.mark.asyncio
    async def test_search_with_results(self, repo, mock_db):
        """測試搜尋 - 有結果"""
        mock_users = [MagicMock(spec=User, id=i) for i in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = mock_result

        results = await repo.search("test", ["username", "email"])

        assert len(results) == 3
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_empty_term(self, repo, mock_db):
        """測試搜尋 - 空搜尋詞回傳全部"""
        mock_users = [MagicMock(spec=User, id=i) for i in range(5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = mock_result

        results = await repo.search("", ["username"])

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_invalid_fields(self, repo, mock_db):
        """測試搜尋 - 無效欄位名稱"""
        results = await repo.search("test", ["nonexistent_field"])

        assert results == []
