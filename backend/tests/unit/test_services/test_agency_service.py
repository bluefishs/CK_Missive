# -*- coding: utf-8 -*-
"""
AgencyService 單元測試

測試範圍:
- 基礎 CRUD 方法 (get_by_id, create, update, delete)
- 業務特定功能 (get_agency_by_name, get_agencies_with_search, get_total_with_search)
- 統計功能 (get_agency_statistics)
- 智慧匹配功能 (match_agency, _parse_agency_text)
- 工具方法 (exists, get_by_code)

測試策略: Mock AgencyRepository，不使用真實資料庫。

v1.0.0 - 2026-02-06
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.services.agency_service import AgencyService
from app.schemas.agency import AgencyCreate, AgencyUpdate


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_db():
    """建立 mock AsyncSession"""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_agency():
    """建立模擬機關實體"""
    agency = MagicMock()
    agency.id = 1
    agency.agency_name = "桃園市政府"
    agency.agency_short_name = "桃市府"
    agency.agency_code = "A376000I"
    agency.agency_type = "政府機關"
    agency.contact_person = "王小明"
    agency.phone = "03-3322101"
    agency.email = "service@tycg.gov.tw"
    agency.address = "桃園市桃園區縣府路1號"
    agency.notes = "市政府本部"
    agency.created_at = datetime(2026, 1, 1)
    agency.updated_at = datetime(2026, 1, 15)
    return agency


@pytest.fixture
def mock_agency_2():
    """建立第二個模擬機關實體"""
    agency = MagicMock()
    agency.id = 2
    agency.agency_name = "新北市政府"
    agency.agency_short_name = "新北府"
    agency.agency_code = "F376000I"
    agency.agency_type = "政府機關"
    agency.contact_person = None
    agency.phone = None
    agency.email = None
    agency.address = "新北市板橋區中山路1段161號"
    agency.notes = None
    agency.created_at = datetime(2026, 1, 2)
    agency.updated_at = datetime(2026, 1, 16)
    return agency


@pytest.fixture
def service(mock_db):
    """建立 AgencyService，內部 repository 使用 mock"""
    with patch("app.services.agency_service.AgencyRepository") as MockRepo:
        mock_repo = MagicMock()
        # 將所有 async 方法設定為 AsyncMock
        mock_repo.get_by_id = AsyncMock()
        mock_repo.find_one_by = AsyncMock()
        mock_repo.create = AsyncMock()
        mock_repo.update = AsyncMock()
        mock_repo.delete = AsyncMock()
        mock_repo.exists = AsyncMock()
        MockRepo.return_value = mock_repo

        svc = AgencyService(mock_db)
        svc.repository = mock_repo
        yield svc


# ============================================================
# 初始化測試
# ============================================================

class TestAgencyServiceInit:
    """AgencyService 初始化測試"""

    def test_init(self, mock_db):
        """測試 AgencyService 初始化 - 應建立 repository 並設定屬性"""
        with patch("app.services.agency_service.AgencyRepository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo

            svc = AgencyService(mock_db)

            assert svc.db is mock_db
            assert svc.repository is mock_repo
            assert svc.entity_name == "機關"
            MockRepo.assert_called_once_with(mock_db)


# ============================================================
# 基礎 CRUD 測試
# ============================================================

class TestGetById:
    """get_by_id 方法測試"""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_agency):
        """測試 get_by_id - 找到機關時返回機關物件"""
        service.repository.get_by_id.return_value = mock_agency

        result = await service.get_by_id(1)

        assert result is mock_agency
        assert result.id == 1
        assert result.agency_name == "桃園市政府"
        service.repository.get_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        """測試 get_by_id - 找不到機關時返回 None"""
        service.repository.get_by_id.return_value = None

        result = await service.get_by_id(9999)

        assert result is None
        service.repository.get_by_id.assert_awaited_once_with(9999)


class TestGetByField:
    """get_by_field 方法測試"""

    @pytest.mark.asyncio
    async def test_get_by_field(self, service, mock_agency):
        """測試 get_by_field - 根據任意欄位查詢"""
        service.repository.find_one_by.return_value = mock_agency

        result = await service.get_by_field("agency_code", "A376000I")

        assert result is mock_agency
        service.repository.find_one_by.assert_awaited_once_with(agency_code="A376000I")

    @pytest.mark.asyncio
    async def test_get_by_field_not_found(self, service):
        """測試 get_by_field - 找不到記錄時返回 None"""
        service.repository.find_one_by.return_value = None

        result = await service.get_by_field("agency_name", "不存在的機關")

        assert result is None


class TestGetList:
    """get_list 方法測試"""

    @pytest.mark.asyncio
    async def test_get_list_default(self, service, mock_db, mock_agency, mock_agency_2):
        """測試 get_list - 使用預設參數取得列表"""
        # 模擬 db.execute 回傳
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_agency, mock_agency_2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_list()

        assert len(result) == 2
        assert result[0].agency_name == "桃園市政府"
        assert result[1].agency_name == "新北市政府"
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_list_with_pagination(self, service, mock_db, mock_agency):
        """測試 get_list - 帶分頁參數"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_agency]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_list(skip=10, limit=5)

        assert len(result) == 1
        mock_db.execute.assert_awaited_once()


class TestCreate:
    """create 方法測試"""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_agency):
        """測試 create - 成功建立機關"""
        # 名稱不重複
        service.repository.find_one_by.return_value = None
        service.repository.create.return_value = mock_agency

        data = AgencyCreate(agency_name="桃園市政府")

        result = await service.create(data)

        assert result is mock_agency
        service.repository.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_with_all_fields(self, service, mock_agency):
        """測試 create - 帶所有可選欄位"""
        service.repository.find_one_by.return_value = None
        service.repository.create.return_value = mock_agency

        data = AgencyCreate(
            agency_name="桃園市政府",
            agency_short_name="桃市府",
            agency_code="A376000I",
            agency_type="政府機關",
            contact_person="王小明",
            phone="03-3322101",
            address="桃園市桃園區縣府路1號",
            email="service@tycg.gov.tw",
        )

        result = await service.create(data)

        assert result is mock_agency
        # 驗證傳入 repository 的資料包含所有欄位
        call_args = service.repository.create.call_args[0][0]
        assert call_args["agency_name"] == "桃園市政府"
        assert call_args["agency_short_name"] == "桃市府"
        assert call_args["agency_code"] == "A376000I"
        assert call_args["agency_type"] == "政府機關"

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises(self, service, mock_agency):
        """測試 create - 機關名稱重複時拋出 ValueError"""
        # 名稱已存在
        service.repository.find_one_by.return_value = mock_agency

        data = AgencyCreate(agency_name="桃園市政府")

        with pytest.raises(ValueError, match="機關名稱已存在"):
            await service.create(data)

        # 確認不會呼叫 repository.create
        service.repository.create.assert_not_awaited()


class TestUpdate:
    """update 方法測試"""

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_agency):
        """測試 update - 成功更新機關"""
        updated_agency = MagicMock()
        updated_agency.id = 1
        updated_agency.agency_name = "桃園市政府(更新)"
        service.repository.update.return_value = updated_agency

        data = AgencyUpdate(agency_name="桃園市政府(更新)")

        result = await service.update(1, data)

        assert result is updated_agency
        assert result.agency_name == "桃園市政府(更新)"
        service.repository.update.assert_awaited_once()
        # 驗證傳入的更新資料
        call_args = service.repository.update.call_args
        assert call_args[0][0] == 1  # agency_id

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        """測試 update - 機關不存在時返回 None"""
        service.repository.update.return_value = None

        data = AgencyUpdate(agency_name="不存在")

        result = await service.update(9999, data)

        assert result is None


class TestDelete:
    """delete 方法測試"""

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db):
        """測試 delete - 成功刪除（無關聯公文）"""
        # mock DeleteCheckHelper.check_multiple_usages
        with patch(
            "app.services.agency_service.DeleteCheckHelper.check_multiple_usages",
            new_callable=AsyncMock,
            return_value=(True, 0),
        ):
            service.repository.delete.return_value = True

            result = await service.delete(1)

            assert result is True
            service.repository.delete.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_db):
        """測試 delete - 機關不存在時返回 False"""
        with patch(
            "app.services.agency_service.DeleteCheckHelper.check_multiple_usages",
            new_callable=AsyncMock,
            return_value=(True, 0),
        ):
            service.repository.delete.return_value = False

            result = await service.delete(9999)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_related_documents_raises(self, service, mock_db):
        """測試 delete - 有關聯公文時拋出 ValueError"""
        with patch(
            "app.services.agency_service.DeleteCheckHelper.check_multiple_usages",
            new_callable=AsyncMock,
            return_value=(False, 5),
        ):
            with pytest.raises(ValueError, match="無法刪除.*5 筆公文"):
                await service.delete(1)

            # 確認不會實際刪除
            service.repository.delete.assert_not_awaited()


# ============================================================
# 業務擴充功能測試
# ============================================================

class TestGetAgencyByName:
    """get_agency_by_name 方法測試"""

    @pytest.mark.asyncio
    async def test_get_agency_by_name(self, service, mock_agency):
        """測試 get_agency_by_name - 根據名稱取得機關"""
        service.repository.find_one_by.return_value = mock_agency

        result = await service.get_agency_by_name("桃園市政府")

        assert result is mock_agency
        service.repository.find_one_by.assert_awaited_once_with(agency_name="桃園市政府")

    @pytest.mark.asyncio
    async def test_get_agency_by_name_not_found(self, service):
        """測試 get_agency_by_name - 名稱不存在"""
        service.repository.find_one_by.return_value = None

        result = await service.get_agency_by_name("不存在的機關")

        assert result is None


class TestGetAgenciesWithSearch:
    """get_agencies_with_search 方法測試"""

    @pytest.mark.asyncio
    async def test_get_agencies_with_search(self, service, mock_db, mock_agency):
        """測試 get_agencies_with_search - 帶搜尋條件"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_agency]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_agencies_with_search(
            skip=0, limit=20, search="桃園"
        )

        # 應返回字典格式的列表
        assert len(result) == 1
        assert result[0]["agency_name"] == "桃園市政府"
        assert result[0]["id"] == 1
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_agencies_with_search_no_results(self, service, mock_db):
        """測試 get_agencies_with_search - 無搜尋結果"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_agencies_with_search(search="不存在")

        assert len(result) == 0


class TestGetTotalWithSearch:
    """get_total_with_search 方法測試"""

    @pytest.mark.asyncio
    async def test_get_total_with_search(self, service, mock_db):
        """測試 get_total_with_search - 帶搜尋條件的計數"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await service.get_total_with_search(search="桃園")

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_total_with_search_no_filter(self, service, mock_db):
        """測試 get_total_with_search - 不帶搜尋條件（全部計數）"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        result = await service.get_total_with_search()

        assert result == 100

    @pytest.mark.asyncio
    async def test_get_total_with_search_returns_zero(self, service, mock_db):
        """測試 get_total_with_search - scalar 返回 None 時回傳 0"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_total_with_search(search="不存在")

        assert result == 0


# ============================================================
# 統計功能測試
# ============================================================

class TestGetAgencyStatistics:
    """get_agency_statistics 方法測試"""

    @pytest.mark.asyncio
    async def test_get_agency_statistics(self, service, mock_db):
        """測試 get_agency_statistics - 返回統計字典"""
        with patch(
            "app.services.agency_service.StatisticsHelper.get_basic_stats",
            new_callable=AsyncMock,
            return_value={"total": 50},
        ), patch(
            "app.services.agency_service.StatisticsHelper.get_grouped_stats",
            new_callable=AsyncMock,
            return_value={"政府機關": 30, "民間企業": 15, "null": 5},
        ):
            result = await service.get_agency_statistics()

            assert result["total_agencies"] == 50
            assert len(result["categories"]) == 3

            # 驗證分類正確
            category_names = [c["category"] for c in result["categories"]]
            assert "政府機關" in category_names
            assert "民間企業" in category_names
            assert "其他單位" in category_names

            # 驗證百分比計算
            gov = next(c for c in result["categories"] if c["category"] == "政府機關")
            assert gov["count"] == 30
            assert gov["percentage"] == 60.0  # 30/50*100

    @pytest.mark.asyncio
    async def test_get_agency_statistics_error(self, service, mock_db):
        """測試 get_agency_statistics - 異常時返回空結構"""
        with patch(
            "app.services.agency_service.StatisticsHelper.get_basic_stats",
            new_callable=AsyncMock,
            side_effect=Exception("資料庫連線失敗"),
        ):
            result = await service.get_agency_statistics()

            assert result["total_agencies"] == 0
            assert result["categories"] == []


# ============================================================
# 智慧匹配功能測試
# ============================================================

class TestMatchAgency:
    """match_agency 方法測試"""

    @pytest.mark.asyncio
    async def test_match_agency_exact_by_code(self, service, mock_agency):
        """測試 match_agency - 透過機關代碼精確匹配"""
        service.repository.find_one_by.return_value = mock_agency

        result = await service.match_agency("A376000I (桃園市政府)")

        assert result is mock_agency

    @pytest.mark.asyncio
    async def test_match_agency_exact_by_name(self, service, mock_db, mock_agency):
        """測試 match_agency - 透過機關名稱精確匹配（無代碼時直接匹配名稱）"""
        # 純名稱文字解析後 code=None，直接進入名稱匹配步驟
        service.repository.find_one_by.return_value = mock_agency

        result = await service.match_agency("桃園市政府")

        assert result is mock_agency
        # 確認呼叫了 find_one_by(agency_name="桃園市政府")
        service.repository.find_one_by.assert_awaited_with(agency_name="桃園市政府")

    @pytest.mark.asyncio
    async def test_match_agency_by_short_name(self, service, mock_db, mock_agency):
        """測試 match_agency - 透過簡稱匹配"""
        # 代碼不匹配，名稱不匹配，簡稱匹配
        service.repository.find_one_by.return_value = None

        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_scalar_result

        result = await service.match_agency("桃市府")

        assert result is mock_agency

    @pytest.mark.asyncio
    async def test_match_agency_fuzzy(self, service, mock_db, mock_agency):
        """測試 match_agency - 部分匹配（機關名稱包含在文字中）"""
        # 前三步都不匹配
        service.repository.find_one_by.return_value = None

        # 第一次 execute (簡稱匹配) 返回 None
        mock_short_name_result = MagicMock()
        mock_short_name_result.scalar_one_or_none.return_value = None

        # 第二次 execute (取得所有機關) 返回列表
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_agency]
        mock_all_result = MagicMock()
        mock_all_result.scalars.return_value = mock_scalars

        mock_db.execute.side_effect = [mock_short_name_result, mock_all_result]

        result = await service.match_agency("函覆桃園市政府有關案件")

        assert result is mock_agency

    @pytest.mark.asyncio
    async def test_match_agency_empty_text(self, service):
        """測試 match_agency - 空文字返回 None"""
        result = await service.match_agency("")
        assert result is None

        result = await service.match_agency("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_match_agency_no_match(self, service, mock_db):
        """測試 match_agency - 完全無匹配返回 None"""
        service.repository.find_one_by.return_value = None

        # 簡稱匹配失敗
        mock_short_name_result = MagicMock()
        mock_short_name_result.scalar_one_or_none.return_value = None

        # 部分匹配也失敗
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_all_result = MagicMock()
        mock_all_result.scalars.return_value = mock_scalars

        mock_db.execute.side_effect = [mock_short_name_result, mock_all_result]

        result = await service.match_agency("完全不存在的東西")

        assert result is None


class TestParseAgencyText:
    """_parse_agency_text 方法測試"""

    def test_parse_simple_name(self, service):
        """測試解析純機關名稱"""
        result = service._parse_agency_text("桃園市政府")
        assert len(result) == 1
        assert result[0] == (None, "桃園市政府")

    def test_parse_code_and_name(self, service):
        """測試解析含代碼的機關文字"""
        result = service._parse_agency_text("A376000I (桃園市政府)")
        assert len(result) == 1
        code, name = result[0]
        assert code == "A376000I"
        assert name == "桃園市政府"

    def test_parse_multiple_agencies(self, service):
        """測試解析多個受文者（以 | 分隔）"""
        result = service._parse_agency_text("A376000I (桃園市政府) | F376000I (新北市政府)")
        assert len(result) == 2

    def test_parse_empty_text(self, service):
        """測試解析空文字"""
        assert service._parse_agency_text("") == []
        assert service._parse_agency_text("   ") == []
        assert service._parse_agency_text(None) == []


# ============================================================
# 工具方法測試
# ============================================================

class TestExists:
    """exists 方法測試"""

    @pytest.mark.asyncio
    async def test_exists_true(self, service):
        """測試 exists - 機關存在"""
        service.repository.exists.return_value = True

        result = await service.exists(1)

        assert result is True
        service.repository.exists.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_exists_false(self, service):
        """測試 exists - 機關不存在"""
        service.repository.exists.return_value = False

        result = await service.exists(9999)

        assert result is False
        service.repository.exists.assert_awaited_once_with(9999)


class TestGetByCode:
    """get_by_code 方法測試"""

    @pytest.mark.asyncio
    async def test_get_by_code_found(self, service, mock_agency):
        """測試 get_by_code - 找到機關"""
        service.repository.find_one_by.return_value = mock_agency

        result = await service.get_by_code("A376000I")

        assert result is mock_agency
        service.repository.find_one_by.assert_awaited_once_with(agency_code="A376000I")

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, service):
        """測試 get_by_code - 代碼不存在"""
        service.repository.find_one_by.return_value = None

        result = await service.get_by_code("XXXXXX")

        assert result is None


# ============================================================
# 分類標準化測試
# ============================================================

class TestNormalizeCategory:
    """_normalize_category 方法測試"""

    def test_normalize_government(self, service):
        """測試政府機關類型標準化"""
        assert service._normalize_category("政府機關") == "政府機關"

    def test_normalize_private(self, service):
        """測試民間企業類型標準化"""
        assert service._normalize_category("民間企業") == "民間企業"

    def test_normalize_other(self, service):
        """測試其他類型標準化為「其他單位」"""
        assert service._normalize_category("社會團體") == "其他單位"
        assert service._normalize_category("教育機構") == "其他單位"
        assert service._normalize_category("其他機關") == "其他單位"

    def test_normalize_none(self, service):
        """測試空值標準化為「其他單位」"""
        assert service._normalize_category(None) == "其他單位"
        assert service._normalize_category("") == "其他單位"


class TestCategorizeAgency:
    """_categorize_agency 方法測試"""

    def test_categorize_government(self, service):
        """測試根據名稱推斷政府機關"""
        assert service._categorize_agency("桃園市政府") == "政府機關"
        assert service._categorize_agency("內政部") == "政府機關"
        assert service._categorize_agency("環保局") == "政府機關"

    def test_categorize_private(self, service):
        """測試根據名稱推斷民間企業"""
        assert service._categorize_agency("台積電公司") == "民間企業"
        assert service._categorize_agency("鴻海集團") == "民間企業"

    def test_categorize_other(self, service):
        """測試無法辨識時歸為其他"""
        assert service._categorize_agency("某協會") == "其他單位"
        assert service._categorize_agency("") == "其他單位"


# ============================================================
# _to_dict 轉換測試
# ============================================================

class TestToDict:
    """_to_dict 方法測試"""

    def test_to_dict(self, service, mock_agency):
        """測試機關實體轉字典"""
        result = service._to_dict(mock_agency)

        assert result["id"] == 1
        assert result["agency_name"] == "桃園市政府"
        assert result["agency_short_name"] == "桃市府"
        assert result["agency_code"] == "A376000I"
        assert result["agency_type"] == "政府機關"
        assert result["contact_person"] == "王小明"
        assert result["phone"] == "03-3322101"
        assert result["email"] == "service@tycg.gov.tw"
        assert result["address"] == "桃園市桃園區縣府路1號"
        assert result["notes"] == "市政府本部"
        assert result["created_at"] == datetime(2026, 1, 1)
        assert result["updated_at"] == datetime(2026, 1, 15)
