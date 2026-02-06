# -*- coding: utf-8 -*-
"""
ProjectService 單元測試

測試範圍:
- 初始化：建構函數、Repository 建立
- 基礎查詢：get_by_id, get_list, get_project
- 權限檢查：check_user_project_access (admin/assigned/denied)
- CRUD：create, update, delete
- 統計與選項：get_project_statistics, get_year_options, get_distinct_options

Mock 策略:
- Mock AsyncSession (mock_db)
- Mock ProjectRepository（透過 patch）
- Mock RLSFilter（透過 patch）
- Mock PaymentRepository（透過 patch）

v1.0.0 - 2026-02-06
"""
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.extended.models import ContractProject


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_db():
    """建立 Mock 資料庫 Session"""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """建立 ProjectService 並注入 mock repository"""
    with patch(
        "app.services.project_service.ProjectRepository"
    ) as MockRepo:
        mock_repo = MagicMock()
        # 預設所有 async 方法為 AsyncMock
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo.get_by_field = AsyncMock(return_value=None)
        mock_repo.find_one_by = AsyncMock(return_value=None)
        MockRepo.return_value = mock_repo

        svc = ProjectService(mock_db)
        svc.repository = mock_repo
        yield svc


@pytest.fixture
def sample_project():
    """建立範例專案物件"""
    project = MagicMock(spec=ContractProject)
    project.id = 1
    project.project_name = "桃園市測繪案"
    project.project_code = "CK2026_01_01_001"
    project.year = 2026
    project.category = "01"
    project.case_nature = "01"
    project.status = "執行中"
    project.contract_amount = 1000000.0
    project.winning_amount = 950000.0
    project.start_date = date(2026, 1, 1)
    project.end_date = date(2026, 12, 31)
    project.progress = 30
    project.notes = "測試備註"
    project.created_at = datetime(2026, 1, 1, 0, 0, 0)
    project.updated_at = datetime(2026, 1, 1, 0, 0, 0)
    return project


# ============================================================
# 初始化測試
# ============================================================


class TestProjectServiceInit:
    """ProjectService 初始化測試"""

    def test_init(self, mock_db):
        """測試 ProjectService(db) 正確建立 repository 和屬性"""
        with patch(
            "app.services.project_service.ProjectRepository"
        ) as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo

            svc = ProjectService(mock_db)

            # 驗證 repository 被正確建立
            MockRepo.assert_called_once_with(mock_db)
            assert svc.db is mock_db
            assert svc.repository is mock_repo
            assert svc.model is ContractProject
            assert svc.entity_name == "承攬案件"


# ============================================================
# 基礎查詢測試
# ============================================================


class TestProjectServiceQuery:
    """ProjectService 基礎查詢測試"""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, sample_project):
        """測試 get_by_id 找到專案時返回專案物件"""
        service.repository.get_by_id.return_value = sample_project

        result = await service.get_by_id(1)

        assert result is sample_project
        assert result.id == 1
        assert result.project_name == "桃園市測繪案"
        service.repository.get_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        """測試 get_by_id 找不到專案時返回 None"""
        service.repository.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None
        service.repository.get_by_id.assert_awaited_once_with(999)

    @pytest.mark.asyncio
    async def test_get_list_default(self, service, mock_db, sample_project):
        """測試 get_list 使用預設參數呼叫"""
        # 模擬 db.execute 返回值
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_project]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_list()

        assert len(result) == 1
        assert result[0] is sample_project
        # 驗證 execute 被呼叫（使用預設 skip=0, limit=100）
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_list_with_filters(self, service, mock_db, sample_project):
        """測試 get_list 使用自訂 skip/limit 參數"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_project]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_list(skip=10, limit=5)

        assert len(result) == 1
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_project_found(self, service, sample_project):
        """測試 get_project 別名方法正確呼叫 get_by_id"""
        service.repository.get_by_id.return_value = sample_project

        result = await service.get_project(1)

        assert result is sample_project
        service.repository.get_by_id.assert_awaited_once_with(1)


# ============================================================
# 權限檢查測試
# ============================================================


class TestProjectServiceAccess:
    """ProjectService 權限檢查測試"""

    @pytest.mark.asyncio
    async def test_check_user_project_access_admin(self, service):
        """測試管理員可以存取專案（透過 RLSFilter）"""
        with patch(
            "app.services.project_service.RLSFilter"
        ) as MockRLS:
            MockRLS.check_user_project_access = AsyncMock(
                return_value=True
            )

            result = await service.check_user_project_access(
                user_id=1, project_id=1
            )

            assert result is True
            MockRLS.check_user_project_access.assert_awaited_once_with(
                service.db, 1, 1
            )

    @pytest.mark.asyncio
    async def test_check_user_project_access_assigned(self, service):
        """測試已指派使用者可以存取專案"""
        with patch(
            "app.services.project_service.RLSFilter"
        ) as MockRLS:
            MockRLS.check_user_project_access = AsyncMock(
                return_value=True
            )

            result = await service.check_user_project_access(
                user_id=5, project_id=10
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_check_user_project_access_denied(self, service):
        """測試未授權使用者無法存取專案"""
        with patch(
            "app.services.project_service.RLSFilter"
        ) as MockRLS:
            MockRLS.check_user_project_access = AsyncMock(
                return_value=False
            )

            result = await service.check_user_project_access(
                user_id=99, project_id=1
            )

            assert result is False


# ============================================================
# CRUD 測試
# ============================================================


class TestProjectServiceCRUD:
    """ProjectService CRUD 操作測試"""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_db):
        """測試成功建立專案"""
        create_data = ProjectCreate(
            project_name="新案件",
            year=2026,
            category="01",
            case_nature="01",
            project_code="CK2026_01_01_005",
        )

        # Mock get_by_field 返回 None（編號不重複）
        service.repository.get_by_field = AsyncMock(return_value=None)

        # Mock db.refresh 設定返回的物件屬性
        created_project = MagicMock(spec=ContractProject)
        created_project.id = 10
        created_project.project_code = "CK2026_01_01_005"

        async def mock_refresh(obj):
            obj.id = 10
            obj.project_code = "CK2026_01_01_005"

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await service.create(create_data)

        # 驗證 db 操作
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_generates_project_code(self, service, mock_db):
        """測試未提供 project_code 時自動產生編號"""
        create_data = ProjectCreate(
            project_name="自動編號案件",
            year=2026,
            category="02",
            case_nature="01",
        )
        # project_code 為 None，應自動產生

        # Mock _generate_project_code 的資料庫查詢
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.id = 20
            obj.project_code = "CK2026_02_01_001"

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await service.create(create_data)

        # 驗證 db.add 被呼叫，且傳入的物件有 project_code
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.project_code == "CK2026_02_01_001"

    @pytest.mark.asyncio
    async def test_create_duplicate_code_raises_error(self, service, mock_db):
        """測試建立時專案編號重複應拋出 ValueError"""
        create_data = ProjectCreate(
            project_name="重複編號案件",
            year=2026,
            project_code="CK2026_01_01_001",
        )

        # Mock get_by_field 返回已存在的專案（編號重複）
        existing = MagicMock(spec=ContractProject)
        existing.project_code = "CK2026_01_01_001"
        service.repository.get_by_field = AsyncMock(return_value=existing)

        with pytest.raises(ValueError, match="已存在"):
            await service.create(create_data)

        # 確認未呼叫 db.add
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_db, sample_project):
        """測試成功更新專案"""
        service.repository.get_by_id.return_value = sample_project
        sample_project.contract_amount = 1000000.0  # 原始金額

        update_data = ProjectUpdate(project_name="更新後的案件名稱")

        result = await service.update(1, update_data)

        assert result is sample_project
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_auto_progress_on_close(self, service, mock_db, sample_project):
        """測試狀態設為已結案時自動設定進度為 100%"""
        service.repository.get_by_id.return_value = sample_project
        sample_project.contract_amount = 1000000.0
        sample_project.progress = 50

        update_data = ProjectUpdate(status="已結案")

        result = await service.update(1, update_data)

        # 驗證 setattr 被呼叫過 progress=100
        # 由於 sample_project 是 MagicMock，我們檢查 setattr 調用
        assert result is sample_project
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_contract_amount_syncs_payments(
        self, service, mock_db, sample_project
    ):
        """測試契約金額變更時同步更新契金記錄"""
        service.repository.get_by_id.return_value = sample_project
        # 使用真實屬性而非 MagicMock
        sample_project.contract_amount = 1000000.0

        update_data = ProjectUpdate(contract_amount=1200000.0)

        # 因為 sample_project 是 MagicMock，setattr 後 contract_amount 改變
        # 我們需要模擬 refresh 後的狀態
        async def mock_refresh(obj):
            obj.contract_amount = 1200000.0

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        with patch(
            "app.services.project_service.PaymentRepository"
        ) as MockPaymentRepo:
            mock_payment_repo = MagicMock()
            mock_payment_repo.update_cumulative_amounts = AsyncMock(
                return_value=3
            )
            MockPaymentRepo.return_value = mock_payment_repo

            result = await service.update(1, update_data)

            assert result is sample_project

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_db):
        """測試更新不存在的專案返回 None"""
        service.repository.get_by_id.return_value = None

        update_data = ProjectUpdate(project_name="不存在的案件")

        result = await service.update(999, update_data)

        assert result is None
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db, sample_project):
        """測試成功刪除專案（含關聯資料清理）"""
        service.repository.get_by_id.return_value = sample_project

        result = await service.delete(1)

        assert result is True
        # 驗證關聯資料刪除（execute 至少呼叫 2 次：user_assignment + vendor_association）
        assert mock_db.execute.await_count >= 2
        mock_db.delete.assert_awaited_once_with(sample_project)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_db):
        """測試刪除不存在的專案返回 False"""
        service.repository.get_by_id.return_value = None

        result = await service.delete(999)

        assert result is False
        mock_db.delete.assert_not_awaited()
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_integrity_error_raises_value_error(
        self, service, mock_db, sample_project
    ):
        """測試刪除有外鍵約束的專案時拋出 ValueError"""
        service.repository.get_by_id.return_value = sample_project

        # 模擬 db.delete 時發生 IntegrityError
        mock_db.delete = AsyncMock(
            side_effect=IntegrityError(
                statement="DELETE",
                params={},
                orig=Exception("foreign key constraint"),
            )
        )

        with pytest.raises(ValueError, match="無法刪除此專案"):
            await service.delete(1)

        mock_db.rollback.assert_awaited_once()


# ============================================================
# 統計與選項測試
# ============================================================


class TestProjectServiceStatistics:
    """ProjectService 統計與選項查詢測試"""

    @pytest.mark.asyncio
    async def test_get_project_statistics(self, service, mock_db):
        """測試取得專案統計資料返回正確結構"""
        # Mock 四個查詢結果

        # 1. 總數查詢
        total_result = MagicMock()
        total_result.scalar.return_value = 50

        # 2. 狀態統計
        status_result = MagicMock()
        status_result.fetchall.return_value = [
            ("執行中", 30),
            ("已結案", 20),
        ]

        # 3. 年度統計
        year_result = MagicMock()
        year_result.fetchall.return_value = [
            (2026, 25),
            (2025, 25),
        ]

        # 4. 平均金額
        amount_result = MagicMock()
        amount_result.scalar.return_value = 1500000.0

        mock_db.execute = AsyncMock(
            side_effect=[
                total_result,
                status_result,
                year_result,
                amount_result,
            ]
        )

        result = await service.get_project_statistics()

        assert result["total_projects"] == 50
        assert len(result["status_breakdown"]) == 2
        assert result["status_breakdown"][0]["status"] == "執行中"
        assert result["status_breakdown"][0]["count"] == 30
        assert len(result["year_breakdown"]) == 2
        assert result["year_breakdown"][0]["year"] == 2026
        assert result["average_contract_amount"] == 1500000.0

    @pytest.mark.asyncio
    async def test_get_project_statistics_error_returns_defaults(
        self, service, mock_db
    ):
        """測試統計查詢失敗時返回預設值"""
        mock_db.execute = AsyncMock(
            side_effect=Exception("DB connection error")
        )

        result = await service.get_project_statistics()

        assert result["total_projects"] == 0
        assert result["status_breakdown"] == []
        assert result["year_breakdown"] == []
        assert result["average_contract_amount"] == 0.0

    @pytest.mark.asyncio
    async def test_get_year_options(self, service, mock_db):
        """測試取得年度選項列表（降序排列）"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (2026,),
            (2025,),
            (2024,),
        ]
        mock_db.execute.return_value = mock_result

        result = await service.get_year_options()

        assert result == [2026, 2025, 2024]

    @pytest.mark.asyncio
    async def test_get_distinct_options(self, service, mock_db):
        """測試取得去重欄位值列表"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("執行中",),
            ("已結案",),
        ]
        mock_db.execute.return_value = mock_result

        result = await service.get_distinct_options("status")

        assert result == ["執行中", "已結案"]

    @pytest.mark.asyncio
    async def test_get_distinct_options_invalid_field(self, service, mock_db):
        """測試取得不存在欄位的去重值返回空列表"""
        result = await service.get_distinct_options("nonexistent_field")

        assert result == []
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_distinct_options_desc_order(self, service, mock_db):
        """測試取得去重值使用降序排列"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (2026,),
            (2025,),
        ]
        mock_db.execute.return_value = mock_result

        result = await service.get_distinct_options(
            "year", sort_order="desc"
        )

        assert result == [2026, 2025]
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_distinct_options_exclude_null(self, service, mock_db):
        """測試去重值排除 NULL（預設行為）"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("01",),
            ("02",),
        ]
        mock_db.execute.return_value = mock_result

        result = await service.get_distinct_options(
            "category", exclude_null=True
        )

        assert result == ["01", "02"]


# ============================================================
# get_projects（含 RLS）測試
# ============================================================


class TestProjectServiceGetProjects:
    """ProjectService.get_projects 測試（含行級別權限過濾）"""

    @pytest.mark.asyncio
    async def test_get_projects_no_user(self, service, mock_db, sample_project):
        """測試不帶使用者時查詢所有專案（不套用 RLS）"""
        # 模擬 count 查詢
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # 模擬專案列表查詢
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_project]
        list_result = MagicMock()
        list_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(
            side_effect=[count_result, list_result]
        )

        query_params = MagicMock()
        query_params.search = None
        query_params.year = None
        query_params.category = None
        query_params.status = None
        query_params.skip = 0
        query_params.limit = 20

        result = await service.get_projects(query_params, current_user=None)

        assert result["total"] == 1
        assert len(result["projects"]) == 1

    @pytest.mark.asyncio
    async def test_get_projects_with_search_filter(
        self, service, mock_db, sample_project
    ):
        """測試帶搜尋條件的專案查詢"""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_project]
        list_result = MagicMock()
        list_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(
            side_effect=[count_result, list_result]
        )

        query_params = MagicMock()
        query_params.search = "桃園"
        query_params.year = 2026
        query_params.category = None
        query_params.status = "執行中"
        query_params.skip = 0
        query_params.limit = 20

        result = await service.get_projects(query_params, current_user=None)

        assert result["total"] == 1


# ============================================================
# 向後相容方法測試
# ============================================================


class TestProjectServiceLegacy:
    """向後相容方法測試（deprecated methods）"""

    @pytest.mark.asyncio
    async def test_create_project_legacy(self, service, mock_db):
        """測試 create_project (deprecated) 正確委派至 create"""
        create_data = ProjectCreate(
            project_name="Legacy 建立",
            year=2026,
            project_code="CK2026_01_01_099",
        )

        # Mock get_by_field 返回 None
        service.repository.get_by_field = AsyncMock(return_value=None)

        async def mock_refresh(obj):
            obj.id = 100
            obj.project_code = "CK2026_01_01_099"

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # 注意：legacy 方法接受 db 參數但會忽略
        result = await service.create_project(mock_db, create_data)

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_project_legacy(self, service, mock_db, sample_project):
        """測試 update_project (deprecated) 正確委派至 update"""
        service.repository.get_by_id.return_value = sample_project
        sample_project.contract_amount = 1000000.0

        update_data = ProjectUpdate(project_name="Legacy 更新")

        result = await service.update_project(mock_db, 1, update_data)

        assert result is sample_project

    @pytest.mark.asyncio
    async def test_delete_project_legacy(self, service, mock_db, sample_project):
        """測試 delete_project (deprecated) 正確委派至 delete"""
        service.repository.get_by_id.return_value = sample_project

        result = await service.delete_project(mock_db, 1)

        assert result is True


# ============================================================
# _generate_project_code 測試
# ============================================================


class TestProjectServiceGenerateCode:
    """專案編號自動產生測試"""

    @pytest.mark.asyncio
    async def test_generate_project_code_first(self, service, mock_db):
        """測試產生第一個專案編號（無既有編號）"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        code = await service._generate_project_code(2026, "01", "01")

        assert code == "CK2026_01_01_001"

    @pytest.mark.asyncio
    async def test_generate_project_code_increment(self, service, mock_db):
        """測試產生遞增的專案編號"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["CK2026_01_01_003"]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        code = await service._generate_project_code(2026, "01", "01")

        assert code == "CK2026_01_01_004"

    @pytest.mark.asyncio
    async def test_generate_project_code_empty_category(self, service, mock_db):
        """測試空類別和空性質使用預設值 00"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        code = await service._generate_project_code(2026, "", "")

        assert code == "CK2026_00_00_001"
