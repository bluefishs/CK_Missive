# -*- coding: utf-8 -*-
"""
VendorService 單元測試

測試範圍:
- VendorService 初始化
- 基礎 CRUD 方法 (get_by_id, get_list, create, update, delete)
- 分頁查詢 (get_paginated, get_count)
- 統計方法 (get_statistics)
- 工具方法 (exists, get_by_code, to_dict)
- 刪除保護 (關聯檢查)

測試策略:
- Mock VendorRepository，不使用真實資料庫
- Mock DeleteCheckHelper / StatisticsHelper 靜態方法
- 使用 AsyncMock 模擬非同步方法

v1.0.0 - 2026-02-06
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import PartnerVendor
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.services.vendor_service import VendorService


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """建立 Mock 資料庫 session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_repository():
    """建立 Mock VendorRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.exists = AsyncMock()
    repo.get_by_field = AsyncMock()
    repo.find_one_by = AsyncMock()
    return repo


@pytest.fixture
def service(mock_db, mock_repository):
    """建立測試用 VendorService，注入 mock repository"""
    with patch("app.services.vendor_service.VendorRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repository
        svc = VendorService(mock_db)
        # 確保使用 mock repository
        svc.repository = mock_repository
        return svc


def _make_vendor(
    vendor_id: int = 1,
    vendor_name: str = "測試廠商",
    vendor_code: str = "V-001",
    contact_person: str = "王小明",
    phone: str = "02-12345678",
    address: str = "台北市中正區",
    email: str = "test@example.com",
    business_type: str = "測量業務",
    rating: int = 4,
) -> MagicMock:
    """建立 Mock 廠商物件"""
    vendor = MagicMock(spec=PartnerVendor)
    vendor.id = vendor_id
    vendor.vendor_name = vendor_name
    vendor.vendor_code = vendor_code
    vendor.contact_person = contact_person
    vendor.phone = phone
    vendor.address = address
    vendor.email = email
    vendor.business_type = business_type
    vendor.rating = rating
    vendor.created_at = datetime(2026, 1, 1, 0, 0, 0)
    vendor.updated_at = datetime(2026, 1, 15, 12, 0, 0)
    return vendor


# ============================================================
# 初始化測試
# ============================================================

class TestVendorServiceInit:
    """VendorService 初始化測試"""

    def test_init(self, mock_db):
        """測試 VendorService 初始化時建立 repository"""
        with patch("app.services.vendor_service.VendorRepository") as MockRepoClass:
            mock_repo_instance = MagicMock()
            MockRepoClass.return_value = mock_repo_instance

            svc = VendorService(mock_db)

            # 驗證 repository 被建立
            MockRepoClass.assert_called_once_with(mock_db)
            assert svc.db is mock_db
            assert svc.repository is mock_repo_instance
            assert svc.model is PartnerVendor


# ============================================================
# get_by_id 測試
# ============================================================

class TestGetById:
    """根據 ID 取得廠商"""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_repository):
        """測試取得存在的廠商"""
        mock_vendor = _make_vendor(vendor_id=1, vendor_name="測試廠商")
        mock_repository.get_by_id.return_value = mock_vendor

        result = await service.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.vendor_name == "測試廠商"
        mock_repository.get_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_repository):
        """測試取得不存在的廠商回傳 None"""
        mock_repository.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None
        mock_repository.get_by_id.assert_awaited_once_with(999)


# ============================================================
# get_list 測試
# ============================================================

class TestGetList:
    """廠商列表查詢"""

    @pytest.mark.asyncio
    async def test_get_list_default(self, service, mock_db):
        """測試預設參數的列表查詢"""
        mock_vendors = [_make_vendor(vendor_id=i) for i in range(3)]

        # mock db.execute 回傳鏈
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_vendors
        mock_db.execute.return_value = mock_result

        result = await service.get_list()

        assert len(result) == 3
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_list_with_search(self, service, mock_db):
        """測試帶搜尋關鍵字的列表查詢"""
        mock_vendors = [_make_vendor(vendor_id=1, vendor_name="桃園建設")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_vendors
        mock_db.execute.return_value = mock_result

        result = await service.get_list(search="桃園")

        assert len(result) == 1
        assert result[0].vendor_name == "桃園建設"
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_list_with_business_type(self, service, mock_db):
        """測試帶營業項目篩選的列表查詢"""
        mock_vendors = [_make_vendor(vendor_id=1, business_type="測量業務")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_vendors
        mock_db.execute.return_value = mock_result

        result = await service.get_list(business_type="測量業務")

        assert len(result) == 1
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_list_with_rating(self, service, mock_db):
        """測試帶評價篩選的列表查詢"""
        mock_vendors = [_make_vendor(vendor_id=1, rating=5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_vendors
        mock_db.execute.return_value = mock_result

        result = await service.get_list(rating=5)

        assert len(result) == 1
        mock_db.execute.assert_awaited_once()


# ============================================================
# get_count 測試
# ============================================================

class TestGetCount:
    """廠商總數查詢"""

    @pytest.mark.asyncio
    async def test_get_count(self, service, mock_db):
        """測試取得廠商總數"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        result = await service.get_count()

        assert result == 42
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_count_with_search(self, service, mock_db):
        """測試帶搜尋條件的廠商總數"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await service.get_count(search="建設")

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_count_returns_zero_when_none(self, service, mock_db):
        """測試 scalar 回傳 None 時返回 0"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_count()

        assert result == 0


# ============================================================
# get_paginated 測試
# ============================================================

class TestGetPaginated:
    """分頁查詢"""

    @pytest.mark.asyncio
    async def test_get_paginated(self, service):
        """測試分頁查詢回傳正確結構"""
        mock_vendors = [_make_vendor(vendor_id=i) for i in range(1, 4)]

        # mock get_list 和 get_count（因為 get_paginated 內部呼叫它們）
        with patch.object(service, "get_list", new_callable=AsyncMock) as mock_get_list, \
             patch.object(service, "get_count", new_callable=AsyncMock) as mock_get_count:
            mock_get_list.return_value = mock_vendors
            mock_get_count.return_value = 25

            result = await service.get_paginated(page=1, page_size=20)

            assert result["items"] == mock_vendors
            assert result["total"] == 25
            assert result["page"] == 1
            assert result["page_size"] == 20
            assert result["total_pages"] == 2  # ceil(25 / 20) = 2

            # 驗證 get_list 被正確呼叫：skip = (1-1)*20 = 0
            mock_get_list.assert_awaited_once_with(
                skip=0,
                limit=20,
                search=None,
                business_type=None,
                rating=None,
            )

    @pytest.mark.asyncio
    async def test_get_paginated_page_2(self, service):
        """測試第二頁分頁查詢"""
        mock_vendors = [_make_vendor(vendor_id=21)]

        with patch.object(service, "get_list", new_callable=AsyncMock) as mock_get_list, \
             patch.object(service, "get_count", new_callable=AsyncMock) as mock_get_count:
            mock_get_list.return_value = mock_vendors
            mock_get_count.return_value = 25

            result = await service.get_paginated(page=2, page_size=20)

            assert result["page"] == 2
            assert result["total_pages"] == 2

            # 驗證 skip = (2-1)*20 = 20
            mock_get_list.assert_awaited_once_with(
                skip=20,
                limit=20,
                search=None,
                business_type=None,
                rating=None,
            )

    @pytest.mark.asyncio
    async def test_get_paginated_empty(self, service):
        """測試空結果的分頁查詢"""
        with patch.object(service, "get_list", new_callable=AsyncMock) as mock_get_list, \
             patch.object(service, "get_count", new_callable=AsyncMock) as mock_get_count:
            mock_get_list.return_value = []
            mock_get_count.return_value = 0

            result = await service.get_paginated()

            assert result["items"] == []
            assert result["total"] == 0
            assert result["total_pages"] == 0


# ============================================================
# create 測試
# ============================================================

class TestCreate:
    """建立廠商"""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_repository):
        """測試成功建立廠商"""
        create_data = VendorCreate(vendor_name="新廠商")
        mock_new_vendor = _make_vendor(vendor_id=10, vendor_name="新廠商", vendor_code=None)
        mock_repository.create.return_value = mock_new_vendor

        result = await service.create(create_data)

        assert result.id == 10
        assert result.vendor_name == "新廠商"
        mock_repository.create.assert_awaited_once_with(create_data)

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, service, mock_repository):
        """測試建立含所有欄位的廠商"""
        create_data = VendorCreate(
            vendor_name="全欄位廠商",
            vendor_code="V-FULL-001",
            contact_person="陳大明",
            phone="03-9876543",
            address="桃園市中壢區",
            email="full@example.com",
            business_type="測量業務",
            rating=5,
        )
        mock_new_vendor = _make_vendor(
            vendor_id=11,
            vendor_name="全欄位廠商",
            vendor_code="V-FULL-001",
        )
        # get_by_field 回傳 None 表示統一編號不重複
        mock_repository.get_by_field.return_value = None
        mock_repository.create.return_value = mock_new_vendor

        result = await service.create(create_data)

        assert result.id == 11
        # 驗證有先檢查統一編號是否重複
        mock_repository.get_by_field.assert_awaited_once_with(
            "vendor_code", "V-FULL-001"
        )
        mock_repository.create.assert_awaited_once_with(create_data)

    @pytest.mark.asyncio
    async def test_create_duplicate_vendor_code(self, service, mock_repository):
        """測試建立重複統一編號的廠商應拋出 ValueError"""
        create_data = VendorCreate(
            vendor_name="重複廠商",
            vendor_code="V-DUP-001",
        )
        existing_vendor = _make_vendor(vendor_id=99, vendor_code="V-DUP-001")
        mock_repository.get_by_field.return_value = existing_vendor

        with pytest.raises(ValueError, match="已存在"):
            await service.create(create_data)

        # 不應呼叫 create
        mock_repository.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_without_vendor_code_skips_check(
        self, service, mock_repository
    ):
        """測試建立不含統一編號的廠商不檢查重複"""
        create_data = VendorCreate(vendor_name="無編號廠商")
        mock_new_vendor = _make_vendor(vendor_id=12, vendor_name="無編號廠商")
        mock_repository.create.return_value = mock_new_vendor

        result = await service.create(create_data)

        assert result.id == 12
        # 沒有 vendor_code 時不應呼叫 get_by_field
        mock_repository.get_by_field.assert_not_awaited()


# ============================================================
# update 測試
# ============================================================

class TestUpdate:
    """更新廠商"""

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_repository):
        """測試成功更新廠商"""
        update_data = VendorUpdate(phone="0912-345-678")
        mock_updated_vendor = _make_vendor(
            vendor_id=1, phone="0912-345-678"
        )
        mock_repository.update.return_value = mock_updated_vendor

        result = await service.update(1, update_data)

        assert result is not None
        assert result.phone == "0912-345-678"
        mock_repository.update.assert_awaited_once_with(1, update_data)

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_repository):
        """測試更新不存在的廠商回傳 None"""
        update_data = VendorUpdate(phone="0999-999-999")
        mock_repository.update.return_value = None

        result = await service.update(999, update_data)

        assert result is None
        mock_repository.update.assert_awaited_once_with(999, update_data)


# ============================================================
# delete 測試
# ============================================================

class TestDelete:
    """刪除廠商"""

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_repository):
        """測試成功刪除無關聯的廠商"""
        mock_repository.delete.return_value = True

        with patch(
            "app.services.vendor_service.DeleteCheckHelper.check_association_usage",
            new_callable=AsyncMock,
            return_value=(True, 0),  # can_delete=True, usage_count=0
        ):
            result = await service.delete(1)

        assert result is True
        mock_repository.delete.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_repository):
        """測試刪除不存在的廠商回傳 False"""
        mock_repository.delete.return_value = False

        with patch(
            "app.services.vendor_service.DeleteCheckHelper.check_association_usage",
            new_callable=AsyncMock,
            return_value=(True, 0),
        ):
            result = await service.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_associations(self, service, mock_repository):
        """測試刪除仍有關聯專案的廠商應拋出 ValueError"""
        with patch(
            "app.services.vendor_service.DeleteCheckHelper.check_association_usage",
            new_callable=AsyncMock,
            return_value=(False, 3),  # can_delete=False, usage_count=3
        ):
            with pytest.raises(ValueError, match="無法刪除.*3 個專案關聯"):
                await service.delete(1)

        # 有關聯時不應呼叫 repository.delete
        mock_repository.delete.assert_not_awaited()


# ============================================================
# get_statistics 測試
# ============================================================

class TestGetStatistics:
    """廠商統計"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, service):
        """測試取得廠商統計資料"""
        with patch(
            "app.services.vendor_service.StatisticsHelper.get_basic_stats",
            new_callable=AsyncMock,
            return_value={"total": 50},
        ), patch(
            "app.services.vendor_service.StatisticsHelper.get_grouped_stats",
            new_callable=AsyncMock,
            return_value={"測量業務": 20, "資訊系統": 15, "null": 15},
        ), patch(
            "app.services.vendor_service.StatisticsHelper.get_average_stats",
            new_callable=AsyncMock,
            return_value={"average": 3.75},
        ):
            result = await service.get_statistics()

        assert result["total_vendors"] == 50
        assert result["average_rating"] == 3.75
        assert isinstance(result["business_types"], list)
        # 驗證 null 被轉換為 "未分類"
        type_names = [t["business_type"] for t in result["business_types"]]
        assert "未分類" in type_names

    @pytest.mark.asyncio
    async def test_get_statistics_error_fallback(self, service):
        """測試統計查詢失敗時回傳預設值"""
        with patch(
            "app.services.vendor_service.StatisticsHelper.get_basic_stats",
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ):
            result = await service.get_statistics()

        # 應回傳安全的預設值
        assert result["total_vendors"] == 0
        assert result["business_types"] == []
        assert result["average_rating"] == 0.0


# ============================================================
# exists 測試
# ============================================================

class TestExists:
    """檢查廠商是否存在"""

    @pytest.mark.asyncio
    async def test_exists_true(self, service, mock_repository):
        """測試廠商存在"""
        mock_repository.exists.return_value = True

        result = await service.exists(1)

        assert result is True
        mock_repository.exists.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_exists_false(self, service, mock_repository):
        """測試廠商不存在"""
        mock_repository.exists.return_value = False

        result = await service.exists(999)

        assert result is False
        mock_repository.exists.assert_awaited_once_with(999)


# ============================================================
# get_by_code 測試
# ============================================================

class TestGetByCode:
    """根據統一編號取得廠商"""

    @pytest.mark.asyncio
    async def test_get_by_code(self, service, mock_repository):
        """測試根據統一編號找到廠商"""
        mock_vendor = _make_vendor(vendor_id=1, vendor_code="V-001")
        mock_repository.get_by_field.return_value = mock_vendor

        result = await service.get_by_code("V-001")

        assert result is not None
        assert result.vendor_code == "V-001"
        mock_repository.get_by_field.assert_awaited_once_with(
            "vendor_code", "V-001"
        )

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, service, mock_repository):
        """測試根據統一編號找不到廠商回傳 None"""
        mock_repository.get_by_field.return_value = None

        result = await service.get_by_code("NONEXISTENT")

        assert result is None
        mock_repository.get_by_field.assert_awaited_once_with(
            "vendor_code", "NONEXISTENT"
        )


# ============================================================
# to_dict 測試
# ============================================================

class TestToDict:
    """廠商物件轉換為字典"""

    def test_to_dict(self, service):
        """測試 to_dict 回傳正確結構"""
        vendor = _make_vendor(
            vendor_id=1,
            vendor_name="字典測試廠商",
            vendor_code="V-DICT",
            contact_person="李四",
            phone="0911111111",
            address="新北市板橋區",
            email="dict@example.com",
            business_type="資訊系統",
            rating=3,
        )

        result = service.to_dict(vendor)

        assert result["id"] == 1
        assert result["vendor_name"] == "字典測試廠商"
        assert result["vendor_code"] == "V-DICT"
        assert result["contact_person"] == "李四"
        assert result["phone"] == "0911111111"
        assert result["address"] == "新北市板橋區"
        assert result["email"] == "dict@example.com"
        assert result["business_type"] == "資訊系統"
        assert result["rating"] == 3
        assert "created_at" in result
        assert "updated_at" in result
