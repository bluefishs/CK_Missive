"""
AgencyRepository 單元測試

測試機關（政府機關/民間企業）Repository 的查詢、匹配、統計等方法。
使用 mock AsyncSession，不需要實際資料庫連線。

@version 1.0.0
@date 2026-02-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.agency_repository import AgencyRepository
from app.extended.models import GovernmentAgency, OfficialDocument


class TestAgencyRepositoryBasicCRUD:
    """AgencyRepository 基礎 CRUD 測試"""

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
        """建立 AgencyRepository 實例"""
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db):
        """測試 get_by_id - 找到機關"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.id = 1
        mock_agency.agency_name = "桃園市政府工務局"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.agency_name == "桃園市政府工務局"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """測試 get_by_id - 機關不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(999)

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agency(self, repo, mock_db):
        """測試建立機關"""
        create_data = {
            "agency_name": "新北市政府",
            "agency_short_name": "新北市府",
            "agency_code": "F000000001",
            "agency_type": "政府機關",
            "contact_person": "王小明",
            "phone": "02-22345678",
        }

        result = await repo.create(create_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_agency(self, repo, mock_db):
        """測試更新機關"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        update_data = {"contact_person": "李大明", "phone": "02-33456789"}
        result = await repo.update(1, update_data)

        assert result is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agency(self, repo, mock_db):
        """測試刪除機關"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.delete(1)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_agency)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agency_not_found(self, repo, mock_db):
        """測試刪除不存在的機關"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.delete(999)

        assert result is False
        mock_db.delete.assert_not_called()


class TestAgencyRepositoryQueries:
    """AgencyRepository 機關特定查詢測試"""

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
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_name(self, repo, mock_db):
        """測試根據機關名稱查詢"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.agency_name = "桃園市政府"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_name("桃園市政府")

        assert result is not None
        assert result.agency_name == "桃園市政府"

    @pytest.mark.asyncio
    async def test_get_by_short_name(self, repo, mock_db):
        """測試根據機關簡稱查詢"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.agency_short_name = "桃市府"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_short_name("桃市府")

        assert result is not None
        assert result.agency_short_name == "桃市府"

    @pytest.mark.asyncio
    async def test_get_by_code(self, repo, mock_db):
        """測試根據機關代碼查詢"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.agency_code = "380110000G"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_code("380110000G")

        assert result is not None
        assert result.agency_code == "380110000G"

    @pytest.mark.asyncio
    async def test_filter_agencies_by_type(self, repo, mock_db):
        """測試依機關類型篩選"""
        mock_agencies = [
            MagicMock(spec=GovernmentAgency, id=1, agency_type="政府機關"),
            MagicMock(spec=GovernmentAgency, id=2, agency_type="政府機關"),
            MagicMock(spec=GovernmentAgency, id=3, agency_type="政府機關"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_type("政府機關")

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_government_agencies(self, repo, mock_db):
        """測試取得政府機關列表"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.get_government_agencies()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_private_companies(self, repo, mock_db):
        """測試取得民間企業列表"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.get_private_companies()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_find_by_name_pattern(self, repo, mock_db):
        """測試模式搜尋機關"""
        mock_agencies = [
            MagicMock(spec=GovernmentAgency, id=1, agency_name="桃園市政府"),
            MagicMock(spec=GovernmentAgency, id=2, agency_name="桃園市政府工務局"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.find_by_name_pattern("桃園")

        assert len(result) == 2


class TestAgencyRepositoryMatching:
    """AgencyRepository 智慧匹配測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_match_agency_by_code(self, repo, mock_db):
        """測試智慧匹配 - 完全匹配機關代碼"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.agency_code = "380110000G"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agency
        mock_db.execute.return_value = mock_result

        result = await repo.match_agency("380110000G")

        assert result is not None
        assert result.agency_code == "380110000G"

    @pytest.mark.asyncio
    async def test_match_agency_by_name(self, repo, mock_db):
        """測試智慧匹配 - 完全匹配機關名稱"""
        # 第一次呼叫 (get_by_code) 回傳 None
        # 第二次呼叫 (get_by_name) 回傳匹配的機關
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.agency_name = "桃園市政府"

        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        mock_result_found = MagicMock()
        mock_result_found.scalar_one_or_none.return_value = mock_agency

        mock_db.execute.side_effect = [mock_result_none, mock_result_found]

        result = await repo.match_agency("桃園市政府")

        assert result is not None
        assert result.agency_name == "桃園市政府"

    @pytest.mark.asyncio
    async def test_match_agency_empty_text(self, repo, mock_db):
        """測試智慧匹配 - 空文字"""
        result = await repo.match_agency("")

        assert result is None
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_agency_whitespace_only(self, repo, mock_db):
        """測試智慧匹配 - 僅空白字元"""
        result = await repo.match_agency("   ")

        assert result is None

    @pytest.mark.asyncio
    async def test_suggest_agencies(self, repo, mock_db):
        """測試機關建議 - 正常結果"""
        mock_agencies = [
            MagicMock(
                spec=GovernmentAgency,
                id=1,
                agency_name="桃園市政府",
                agency_code="380000000G",
                agency_short_name="桃市府",
                agency_type="政府機關",
            ),
            MagicMock(
                spec=GovernmentAgency,
                id=2,
                agency_name="桃園市政府工務局",
                agency_code="380110000G",
                agency_short_name="桃市工務局",
                agency_type="政府機關",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.suggest_agencies("桃園")

        assert len(result) == 2
        assert result[0]["agency_name"] == "桃園市政府"
        assert result[1]["agency_name"] == "桃園市政府工務局"

    @pytest.mark.asyncio
    async def test_suggest_agencies_short_text(self, repo, mock_db):
        """測試機關建議 - 文字太短（少於 2 字）"""
        result = await repo.suggest_agencies("桃")

        assert result == []
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_suggest_agencies_empty_text(self, repo, mock_db):
        """測試機關建議 - 空文字"""
        result = await repo.suggest_agencies("")

        assert result == []


class TestAgencyRepositoryDocuments:
    """AgencyRepository 公文關聯查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_sent_documents(self, repo, mock_db):
        """測試取得機關發文列表"""
        mock_docs = [
            MagicMock(spec=OfficialDocument, id=1),
            MagicMock(spec=OfficialDocument, id=2),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_sent_documents(agency_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_received_documents(self, repo, mock_db):
        """測試取得機關收文列表"""
        mock_docs = [MagicMock(spec=OfficialDocument, id=3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_docs
        mock_db.execute.return_value = mock_result

        result = await repo.get_received_documents(agency_id=1)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_document_counts(self, repo, mock_db):
        """測試取得機關的公文統計"""
        mock_sent_result = MagicMock()
        mock_sent_result.scalar.return_value = 10

        mock_received_result = MagicMock()
        mock_received_result.scalar.return_value = 5

        mock_db.execute.side_effect = [mock_sent_result, mock_received_result]

        result = await repo.get_document_counts(agency_id=1)

        assert result["sent"] == 10
        assert result["received"] == 5
        assert result["total"] == 15

    @pytest.mark.asyncio
    async def test_has_related_documents_true(self, repo, mock_db):
        """測試機關有關聯公文"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute.return_value = mock_result

        result = await repo.has_related_documents(agency_id=1)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_related_documents_false(self, repo, mock_db):
        """測試機關無關聯公文"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await repo.has_related_documents(agency_id=999)

        assert result is False


class TestAgencyRepositorySearch:
    """AgencyRepository 搜尋功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_search_agencies(self, repo, mock_db):
        """測試搜尋機關"""
        mock_agencies = [
            MagicMock(spec=GovernmentAgency, id=1, agency_name="桃園市政府"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.search("桃園", repo.SEARCH_FIELDS)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_agencies_empty_term(self, repo, mock_db):
        """測試搜尋 - 空搜尋詞回傳全部"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(10)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agencies
        mock_db.execute.return_value = mock_result

        result = await repo.search("", repo.SEARCH_FIELDS)

        assert len(result) == 10


class TestAgencyRepositoryStatistics:
    """AgencyRepository 統計功能測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_statistics(self, repo, mock_db):
        """測試取得機關統計資料"""
        # count() -> total
        mock_count = MagicMock()
        mock_count.scalar.return_value = 30

        # _get_grouped_count('agency_type')
        mock_type = MagicMock()
        mock_type.fetchall.return_value = [
            ("政府機關", 20),
            ("民間企業", 8),
            ("其他單位", 2),
        ]

        # _get_active_agency_count()
        mock_active = MagicMock()
        mock_active.scalar.return_value = 15

        mock_db.execute.side_effect = [mock_count, mock_type, mock_active]

        result = await repo.get_statistics()

        assert result["total"] == 30
        assert result["by_type"]["政府機關"] == 20
        assert result["by_type"]["民間企業"] == 8
        assert result["by_type"]["其他單位"] == 2
        assert result["active_count"] == 15

    @pytest.mark.asyncio
    async def test_get_type_statistics(self, repo, mock_db):
        """測試取得依類型統計"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("政府機關", 25),
            ("民間企業", 10),
        ]
        mock_db.execute.return_value = mock_result

        result = await repo.get_type_statistics()

        assert result["政府機關"] == 25
        assert result["民間企業"] == 10

    @pytest.mark.asyncio
    async def test_get_statistics_with_null_type(self, repo, mock_db):
        """測試統計 - 含 NULL 類型欄位"""
        mock_count = MagicMock()
        mock_count.scalar.return_value = 10

        mock_type = MagicMock()
        mock_type.fetchall.return_value = [
            ("政府機關", 5),
            (None, 3),
            ("民間企業", 2),
        ]

        mock_active = MagicMock()
        mock_active.scalar.return_value = 4

        mock_db.execute.side_effect = [mock_count, mock_type, mock_active]

        result = await repo.get_statistics()

        assert result["by_type"]["政府機關"] == 5
        assert result["by_type"]["(未設定)"] == 3
        assert result["by_type"]["民間企業"] == 2


class TestAgencyRepositoryPagination:
    """AgencyRepository 分頁測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_paginated_default(self, repo, mock_db):
        """測試分頁查詢 - 預設參數"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(5)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 30

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_agencies

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await repo.get_paginated(page=1, page_size=20)

        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total"] == 30
        assert result["total_pages"] == 2
        assert len(result["items"]) == 5

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


class TestAgencyRepositoryFilterAgencies:
    """AgencyRepository 進階篩選測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_filter_agencies_by_type(self, repo, mock_db):
        """測試進階篩選 - 依類型"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(3)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_agencies

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        agencies, total = await repo.filter_agencies(agency_type="政府機關")

        assert len(agencies) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_filter_agencies_with_search(self, repo, mock_db):
        """測試進階篩選 - 含搜尋條件"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=1)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_agencies

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        agencies, total = await repo.filter_agencies(search="桃園")

        assert len(agencies) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_agencies_with_documents(self, repo, mock_db):
        """測試進階篩選 - 有公文往來的機關"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(2)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_agencies

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        agencies, total = await repo.filter_agencies(has_documents=True)

        assert len(agencies) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_filter_agencies_no_params(self, repo, mock_db):
        """測試進階篩選 - 無篩選條件"""
        mock_agencies = [MagicMock(spec=GovernmentAgency, id=i) for i in range(10)]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_agencies

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        agencies, total = await repo.filter_agencies()

        assert len(agencies) == 10
        assert total == 10

    @pytest.mark.asyncio
    async def test_filter_agencies_sort_desc(self, repo, mock_db):
        """測試進階篩選 - 降序排列"""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        agencies, total = await repo.filter_agencies(
            sort_by="agency_name",
            sort_order="desc",
        )

        assert total == 0
        assert agencies == []


class TestAgencyRepositoryWithDocumentStats:
    """AgencyRepository 含公文統計的查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AgencyRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_with_document_stats_found(self, repo, mock_db):
        """測試取得機關含公文統計 - 找到"""
        mock_agency = MagicMock(spec=GovernmentAgency)
        mock_agency.id = 1
        mock_agency.agency_name = "桃園市政府"
        mock_agency.agency_short_name = "桃市府"
        mock_agency.agency_code = "380000000G"
        mock_agency.agency_type = "政府機關"
        mock_agency.contact_person = "王小明"
        mock_agency.phone = "03-3322101"
        mock_agency.email = "test@taoyuan.gov.tw"
        mock_agency.address = "桃園市桃園區縣府路1號"
        mock_agency.created_at = None
        mock_agency.updated_at = None

        # get_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = mock_agency

        # get_document_counts: sent count
        mock_sent = MagicMock()
        mock_sent.scalar.return_value = 20

        # get_document_counts: received count
        mock_received = MagicMock()
        mock_received.scalar.return_value = 15

        # last_activity
        from datetime import date as dt_date
        mock_activity = MagicMock()
        mock_activity.scalar.return_value = dt_date(2026, 2, 1)

        mock_db.execute.side_effect = [
            mock_get_result,
            mock_sent,
            mock_received,
            mock_activity,
        ]

        result = await repo.get_with_document_stats(agency_id=1)

        assert result is not None
        assert result["agency_name"] == "桃園市政府"
        assert result["document_stats"]["sent"] == 20
        assert result["document_stats"]["received"] == 15
        assert result["document_stats"]["total"] == 35
        assert result["last_activity"] == dt_date(2026, 2, 1)

    @pytest.mark.asyncio
    async def test_get_with_document_stats_not_found(self, repo, mock_db):
        """測試取得機關含公文統計 - 機關不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_with_document_stats(agency_id=999)

        assert result is None
