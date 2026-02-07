"""
ProjectRepository 單元測試

測試專案（承攬案件）Repository 的查詢、篩選、統計等方法。
使用 mock AsyncSession，不需要實際資料庫連線。

@version 1.0.0
@date 2026-02-07
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.project_repository import ProjectRepository
from app.extended.models import ContractProject, OfficialDocument


class TestProjectRepositoryBasicCRUD:
    """ProjectRepository 基礎 CRUD 測試"""

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
        """建立 ProjectRepository 實例"""
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db):
        """測試 get_by_id - 找到專案"""
        mock_project = MagicMock(spec=ContractProject)
        mock_project.id = 1
        mock_project.project_name = "測試案件"
        mock_project.project_code = "CK2026_01_01_001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.project_name == "測試案件"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """測試 get_by_id - 專案不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(999)

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project(self, repo, mock_db):
        """測試建立專案"""
        create_data = {
            "project_name": "新建測試案件",
            "project_code": "CK2026_01_01_002",
            "year": 2026,
            "client_agency": "桃園市政府",
            "status": "執行中",
            "category": "01委辦案件",
            "contract_amount": 500000.0,
        }

        result = await repo.create(create_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_project(self, repo, mock_db):
        """測試更新專案"""
        mock_project = MagicMock(spec=ContractProject)
        mock_project.id = 1
        mock_project.status = "執行中"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute.return_value = mock_result

        update_data = {"status": "已結案", "progress": 100}
        result = await repo.update(1, update_data)

        assert result is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project(self, repo, mock_db):
        """測試刪除專案"""
        mock_project = MagicMock(spec=ContractProject)
        mock_project.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute.return_value = mock_result

        result = await repo.delete(1)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_project)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, repo, mock_db):
        """測試刪除不存在的專案"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.delete(999)

        assert result is False
        mock_db.delete.assert_not_called()


class TestProjectRepositoryQueries:
    """ProjectRepository 專案特定查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_project_code_found(self, repo, mock_db):
        """測試根據專案編號查詢 - 找到"""
        mock_project = MagicMock(spec=ContractProject)
        mock_project.project_code = "CK2026_01_01_001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project_code("CK2026_01_01_001")

        assert result is not None
        assert result.project_code == "CK2026_01_01_001"

    @pytest.mark.asyncio
    async def test_get_by_project_code_not_found(self, repo, mock_db):
        """測試根據專案編號查詢 - 不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project_code("CK9999_99_99_999")

        assert result is None

    @pytest.mark.asyncio
    async def test_filter_projects_by_status(self, repo, mock_db):
        """測試依狀態篩選專案"""
        mock_projects = [
            MagicMock(spec=ContractProject, id=1, status="執行中"),
            MagicMock(spec=ContractProject, id=2, status="執行中"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_status("執行中")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filter_projects_by_year(self, repo, mock_db):
        """測試依年度篩選專案"""
        mock_projects = [
            MagicMock(spec=ContractProject, id=1, year=2026),
            MagicMock(spec=ContractProject, id=2, year=2026),
            MagicMock(spec=ContractProject, id=3, year=2026),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_year(2026)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_active_projects(self, repo, mock_db):
        """測試取得執行中的專案"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(4)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_active_projects()

        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_get_by_category(self, repo, mock_db):
        """測試依類別篩選專案"""
        mock_projects = [MagicMock(spec=ContractProject, id=1, category="01委辦案件")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_category("01委辦案件")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_date_range(self, repo, mock_db):
        """測試依日期範圍篩選專案"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_date_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        assert len(result) == 2


class TestProjectRepositorySearch:
    """ProjectRepository 搜尋功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_search_projects(self, repo, mock_db):
        """測試搜尋專案"""
        mock_projects = [
            MagicMock(spec=ContractProject, id=1, project_name="桃園測量案"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.search("桃園", repo.SEARCH_FIELDS)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_projects_empty_term(self, repo, mock_db):
        """測試搜尋 - 空搜尋詞回傳全部"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.search("", repo.SEARCH_FIELDS)

        assert len(result) == 3


class TestProjectRepositoryUserAccess:
    """ProjectRepository 使用者權限測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_check_user_access_granted(self, repo, mock_db):
        """測試使用者有專案存取權限"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = True
        mock_db.execute.return_value = mock_result

        result = await repo.check_user_access(user_id=1, project_id=1)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_user_access_denied(self, repo, mock_db):
        """測試使用者無專案存取權限"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_db.execute.return_value = mock_result

        result = await repo.check_user_access(user_id=99, project_id=1)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_projects_by_user(self, repo, mock_db):
        """測試取得使用者關聯的專案"""
        mock_projects = [
            MagicMock(spec=ContractProject, id=1),
            MagicMock(spec=ContractProject, id=2),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_projects
        mock_db.execute.return_value = mock_result

        result = await repo.get_projects_by_user(user_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_project_users(self, repo, mock_db):
        """測試取得專案的指派人員"""
        mock_rows = [
            MagicMock(
                id=1,
                username="user1",
                full_name="使用者一",
                email="user1@test.com",
                role="主辦",
                is_primary=True,
                assignment_date=date(2026, 1, 1),
                assignment_id=10,
            ),
            MagicMock(
                id=2,
                username="user2",
                full_name="使用者二",
                email="user2@test.com",
                role="協辦",
                is_primary=False,
                assignment_date=date(2026, 1, 15),
                assignment_id=11,
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        result = await repo.get_project_users(project_id=1)

        assert len(result) == 2
        assert result[0]["username"] == "user1"
        assert result[0]["is_primary"] is True
        assert result[1]["username"] == "user2"
        assert result[1]["is_primary"] is False

    @pytest.mark.asyncio
    async def test_get_primary_user_found(self, repo, mock_db):
        """測試取得專案主要負責人 - 找到"""
        mock_row = MagicMock(
            id=1,
            username="primary_user",
            full_name="主辦人員",
            email="primary@test.com",
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await repo.get_primary_user(project_id=1)

        assert result is not None
        assert result["username"] == "primary_user"

    @pytest.mark.asyncio
    async def test_get_primary_user_not_found(self, repo, mock_db):
        """測試取得專案主要負責人 - 無主辦"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_primary_user(project_id=999)

        assert result is None


class TestProjectRepositoryStatistics:
    """ProjectRepository 統計功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_statistics(self, repo, mock_db):
        """測試取得專案統計資料"""
        # count() -> total
        mock_count = MagicMock()
        mock_count.scalar.return_value = 50

        # _get_grouped_count('status')
        mock_status = MagicMock()
        mock_status.fetchall.return_value = [("執行中", 30), ("已結案", 20)]

        # _get_grouped_count('category')
        mock_category = MagicMock()
        mock_category.fetchall.return_value = [("01委辦案件", 25), ("02協力計畫", 15), ("03小額採購", 10)]

        # _get_yearly_stats -> count subquery
        mock_yearly_count = MagicMock()
        mock_yearly_count.scalar.return_value = 15

        # _get_yearly_stats -> amount
        mock_yearly_amount = MagicMock()
        mock_yearly_amount.scalar.return_value = 5000000

        # _get_total_amount
        mock_total_amount = MagicMock()
        mock_total_amount.scalar.return_value = 25000000

        mock_db.execute.side_effect = [
            mock_count,
            mock_status,
            mock_category,
            mock_yearly_count,
            mock_yearly_amount,
            mock_total_amount,
        ]

        result = await repo.get_statistics()

        assert result["total"] == 50
        assert result["by_status"]["執行中"] == 30
        assert result["by_status"]["已結案"] == 20
        assert result["by_category"]["01委辦案件"] == 25
        assert result["total_contract_amount"] == 25000000.0

    @pytest.mark.asyncio
    async def test_get_project_document_count(self, repo, mock_db):
        """測試取得專案的公文數量"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 12
        mock_db.execute.return_value = mock_result

        result = await repo.get_project_document_count(project_id=1)

        assert result == 12

    @pytest.mark.asyncio
    async def test_get_project_document_count_zero(self, repo, mock_db):
        """測試取得專案的公文數量 - 無公文"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.get_project_document_count(project_id=999)

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_year_options(self, repo, mock_db):
        """測試取得可用的年度選項"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(2026,), (2025,), (2024,)]
        mock_db.execute.return_value = mock_result

        result = await repo.get_year_options()

        assert result == [2026, 2025, 2024]


class TestProjectRepositoryPagination:
    """ProjectRepository 分頁測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_paginated_default(self, repo, mock_db):
        """測試分頁查詢 - 預設參數"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(5)]

        # count 查詢
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        # 資料查詢
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_projects

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await repo.get_paginated(page=1, page_size=20)

        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total"] == 50
        assert result["total_pages"] == 3
        assert len(result["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_paginated_page_2(self, repo, mock_db):
        """測試分頁查詢 - 第 2 頁"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(10)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 25

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_projects

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await repo.get_paginated(page=2, page_size=10)

        assert result["page"] == 2
        assert result["page_size"] == 10
        assert result["total"] == 25
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_get_paginated_empty(self, repo, mock_db):
        """測試分頁查詢 - 無資料"""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await repo.get_paginated(page=1, page_size=20)

        assert result["total"] == 0
        assert result["total_pages"] == 0
        assert result["items"] == []


class TestProjectRepositoryFilterProjects:
    """ProjectRepository 進階篩選測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_filter_projects_all_params(self, repo, mock_db):
        """測試進階篩選 - 多個參數"""
        mock_projects = [MagicMock(spec=ContractProject, id=1)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_projects

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        projects, total = await repo.filter_projects(
            year=2026,
            category="01委辦案件",
            status="執行中",
            search="桃園",
            skip=0,
            limit=20,
        )

        assert len(projects) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_projects_no_params(self, repo, mock_db):
        """測試進階篩選 - 無篩選條件"""
        mock_projects = [MagicMock(spec=ContractProject, id=i) for i in range(5)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_projects

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        projects, total = await repo.filter_projects()

        assert len(projects) == 5
        assert total == 5


class TestProjectRepositoryProjectCode:
    """ProjectRepository 專案編號生成測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return ProjectRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_next_project_code_first(self, repo, mock_db):
        """測試取得下一個專案編號 - 首次建立"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_next_project_code(
            year=2026,
            category="01",
            case_nature="01",
        )

        assert result == "CK2026_01_01_001"

    @pytest.mark.asyncio
    async def test_get_next_project_code_increment(self, repo, mock_db):
        """測試取得下一個專案編號 - 遞增"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = "CK2026_01_01_003"
        mock_db.execute.return_value = mock_result

        result = await repo.get_next_project_code(
            year=2026,
            category="01",
            case_nature="01",
        )

        assert result == "CK2026_01_01_004"

    @pytest.mark.asyncio
    async def test_check_project_code_exists(self, repo, mock_db):
        """測試檢查專案編號是否存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        result = await repo.check_project_code_exists("CK2026_01_01_001")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_project_code_not_exists(self, repo, mock_db):
        """測試檢查專案編號不存在"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.check_project_code_exists("CK9999_99_99_999")

        assert result is False
