"""
標案快取服務單元測試

測試 tender_cache_service.py 的 7 個模組級函數：
- save_search_results: 批次寫入 + 去重 + 空列表
- search_from_db: ILIKE 模糊搜尋
- get_db_stats: 統計回傳結構
- build_graph_from_db: 圖譜節點/邊建構
- cross_reference_pm_cases: 跨服務索引
- normalize_company_names: 廠商名稱正規化
- refresh_pending_tenders: 待更新標案刷新
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db():
    """模擬 AsyncSession"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


def _scalar_result(value):
    """建立回傳 scalar() 值的 mock"""
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _fetchall_result(rows):
    """建立回傳 fetchall() 的 mock"""
    result = MagicMock()
    result.fetchall.return_value = rows
    return result


class TestParseDate:
    """_parse_date 輔助函數測試"""

    def test_valid_date(self):
        from app.services.tender_cache_service import _parse_date
        from datetime import date
        assert _parse_date("2026-04-01") == date(2026, 4, 1)

    def test_empty_string(self):
        from app.services.tender_cache_service import _parse_date
        assert _parse_date("") is None

    def test_none_value(self):
        from app.services.tender_cache_service import _parse_date
        assert _parse_date(None) is None

    def test_invalid_format(self):
        from app.services.tender_cache_service import _parse_date
        assert _parse_date("not-a-date") is None

    def test_long_string_truncated(self):
        from app.services.tender_cache_service import _parse_date
        from datetime import date
        assert _parse_date("2026-04-01T12:00:00") == date(2026, 4, 1)


class TestParseAmount:
    """_parse_amount 輔助函數測試"""

    def test_integer_string(self):
        from app.services.tender_cache_service import _parse_amount
        assert _parse_amount("1000000") == 1000000.0

    def test_comma_separated(self):
        from app.services.tender_cache_service import _parse_amount
        assert _parse_amount("1,000,000") == 1000000.0

    def test_none_returns_none(self):
        from app.services.tender_cache_service import _parse_amount
        assert _parse_amount(None) is None

    def test_empty_string_returns_none(self):
        from app.services.tender_cache_service import _parse_amount
        assert _parse_amount("") is None

    def test_with_currency_symbol(self):
        from app.services.tender_cache_service import _parse_amount
        assert _parse_amount("$5,000") == 5000.0


class TestSaveSearchResults:
    """save_search_results 批次寫入測試"""

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self, mock_db):
        """空記錄列表應回傳 0"""
        from app.services.tender_cache_service import save_search_results
        result = await save_search_results(mock_db, [])
        assert result == 0
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_without_title_skipped(self, mock_db):
        """無 title 的記錄應被跳過"""
        from app.services.tender_cache_service import save_search_results
        records = [{"unit_id": "U1", "job_number": "J1", "title": ""}]
        result = await save_search_results(mock_db, records)
        assert result == 0

    @pytest.mark.asyncio
    async def test_record_without_id_skipped(self, mock_db):
        """無 unit_id 且無 ezbid_id 的記錄應被跳過"""
        from app.services.tender_cache_service import save_search_results
        records = [{"title": "有標題但沒有 ID"}]
        result = await save_search_results(mock_db, records)
        assert result == 0

    @pytest.mark.asyncio
    async def test_existing_record_skipped(self, mock_db):
        """已存在的記錄 (unit_id+job_number 重複) 應跳過"""
        from app.services.tender_cache_service import save_search_results

        # 模擬 SELECT id 回傳已存在的 id
        mock_db.execute.return_value = _scalar_result(42)

        records = [{"unit_id": "U1", "job_number": "J1", "title": "已存在標案"}]
        result = await save_search_results(mock_db, records)
        assert result == 0
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_record_saved_successfully(self, mock_db):
        """新記錄應成功插入並回傳計數 1"""
        from app.services.tender_cache_service import save_search_results

        # 第一次 execute: SELECT (不存在), 第二次: INSERT, 第三次: lastval
        mock_db.execute.side_effect = [
            _scalar_result(None),        # SELECT — not found
            MagicMock(),                 # INSERT
            _scalar_result(100),         # lastval
        ]

        records = [{
            "unit_id": "U1", "job_number": "J1", "title": "新標案",
            "unit_name": "測試機關", "category": "工程", "type": "公開招標",
            "date": "2026-04-01", "budget": "1,000,000", "status": "等標期",
        }]
        result = await save_search_results(mock_db, records, source="pcc")
        assert result == 1
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ezbid_record_uses_ezbid_id_for_dedup(self, mock_db):
        """ezbid 來源的記錄應以 ezbid_id 做去重查詢"""
        from app.services.tender_cache_service import save_search_results

        mock_db.execute.side_effect = [
            _scalar_result(None),   # SELECT by ezbid_id — not found
            MagicMock(),            # INSERT
            _scalar_result(101),    # lastval
        ]

        records = [{
            "ezbid_id": "EZ123", "title": "ezbid 標案",
            "unit_id": "", "job_number": "",
        }]
        result = await save_search_results(mock_db, records, source="ezbid")
        assert result == 1

    @pytest.mark.asyncio
    async def test_winner_and_bidder_links_created(self, mock_db):
        """有 winner_names/bidder_names 時應建立廠商關聯"""
        from app.services.tender_cache_service import save_search_results

        mock_db.execute.side_effect = [
            _scalar_result(None),    # SELECT — not found
            MagicMock(),             # INSERT tender_records
            _scalar_result(200),     # lastval
            MagicMock(),             # INSERT winner link
            MagicMock(),             # INSERT bidder link
        ]

        records = [{
            "unit_id": "U2", "job_number": "J2", "title": "有廠商的標案",
            "winner_names": ["得標公司A"],
            "bidder_names": ["投標公司B"],
        }]
        result = await save_search_results(mock_db, records)
        assert result == 1
        # 5 calls: SELECT + INSERT record + lastval + 2 company links
        assert mock_db.execute.call_count == 5


class TestSearchFromDb:
    """search_from_db 資料庫搜尋測試"""

    @pytest.mark.asyncio
    async def test_returns_list(self, mock_db):
        """應回傳 list of dict"""
        from app.services.tender_cache_service import search_from_db

        mock_db.execute.return_value = _fetchall_result([])
        result = await search_from_db(mock_db, "水利")
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_maps_row_fields_correctly(self, mock_db):
        """應正確映射 DB row 欄位到回傳格式"""
        from app.services.tender_cache_service import search_from_db
        from datetime import date

        row = MagicMock()
        row.announce_date = date(2026, 4, 1)
        row.title = "水利工程標案"
        row.tender_type = "公開招標"
        row.category = "工程"
        row.unit_id = "U1"
        row.unit_name = "水利署"
        row.job_number = "J001"
        row.source = "pcc"
        row.budget = 5000000
        row.winners = ["得標公司"]
        row.bidders = ["投標公司"]

        mock_db.execute.return_value = _fetchall_result([row])
        result = await search_from_db(mock_db, "水利")

        assert len(result) == 1
        r = result[0]
        assert r["title"] == "水利工程標案"
        assert r["unit_name"] == "水利署"
        assert r["source"] == "pcc"
        assert r["budget"] == 5000000.0
        assert r["winner_names"] == ["得標公司"]
        assert r["bidder_names"] == ["投標公司"]
        assert "得標公司" in r["company_names"]

    @pytest.mark.asyncio
    async def test_null_fields_handled(self, mock_db):
        """NULL 欄位應安全處理為空字串或 None"""
        from app.services.tender_cache_service import search_from_db

        row = MagicMock()
        row.announce_date = None
        row.title = None
        row.tender_type = None
        row.category = None
        row.unit_id = None
        row.unit_name = None
        row.job_number = None
        row.source = None
        row.budget = None
        row.winners = None
        row.bidders = None

        mock_db.execute.return_value = _fetchall_result([row])
        result = await search_from_db(mock_db, "test")

        assert len(result) == 1
        r = result[0]
        assert r["title"] == ""
        assert r["date"] == ""
        assert r["budget"] is None


class TestGetDbStats:
    """get_db_stats 統計測試"""

    @pytest.mark.asyncio
    async def test_returns_all_expected_keys(self, mock_db):
        """應回傳包含所有預期 key 的 dict"""
        from app.services.tender_cache_service import get_db_stats
        from datetime import date

        mock_db.execute.side_effect = [
            _scalar_result(100),              # total
            _scalar_result(80),               # pcc
            _scalar_result(20),               # ezbid
            _scalar_result(50),               # companies
            _scalar_result(date(2026, 4, 1)), # latest
            _scalar_result(30),               # awarded
        ]

        result = await get_db_stats(mock_db)
        assert result["total_records"] == 100
        assert result["pcc_records"] == 80
        assert result["ezbid_records"] == 20
        assert result["unique_companies"] == 50
        assert result["awarded_records"] == 30
        assert result["latest_date"] == "2026-04-01"

    @pytest.mark.asyncio
    async def test_empty_db_returns_zeros(self, mock_db):
        """空 DB 應回傳全 0"""
        from app.services.tender_cache_service import get_db_stats

        mock_db.execute.side_effect = [
            _scalar_result(0),     # total
            _scalar_result(0),     # pcc
            _scalar_result(0),     # ezbid
            _scalar_result(0),     # companies
            _scalar_result(None),  # latest
            _scalar_result(0),     # awarded
        ]

        result = await get_db_stats(mock_db)
        assert result["total_records"] == 0
        assert result["latest_date"] is None


class TestBuildGraphFromDb:
    """build_graph_from_db 圖譜建構測試"""

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_graph(self, mock_db):
        """無結果時應回傳空圖譜"""
        from app.services.tender_cache_service import build_graph_from_db

        mock_db.execute.return_value = _fetchall_result([])
        result = await build_graph_from_db(mock_db, "不存在")

        assert result["query"] == "不存在"
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["stats"]["tenders"] == 0

    @pytest.mark.asyncio
    async def test_builds_agency_tender_company_nodes(self, mock_db):
        """應正確建構 機關→標案→廠商 三層節點"""
        from app.services.tender_cache_service import build_graph_from_db
        from datetime import date

        row1 = MagicMock()
        row1.id = 1
        row1.title = "水利工程設計"
        row1.unit_name = "水利署"
        row1.unit_id = "U1"
        row1.job_number = "J1"
        row1.category = "工程"
        row1.announce_date = date(2026, 3, 1)
        row1.company_name = "乾坤工程"
        row1.role = "winner"

        row2 = MagicMock()
        row2.id = 1
        row2.title = "水利工程設計"
        row2.unit_name = "水利署"
        row2.unit_id = "U1"
        row2.job_number = "J1"
        row2.category = "工程"
        row2.announce_date = date(2026, 3, 1)
        row2.company_name = "競爭公司"
        row2.role = "bidder"

        mock_db.execute.return_value = _fetchall_result([row1, row2])
        result = await build_graph_from_db(mock_db, "水利")

        # 應有 1 機關 + 1 標案 + 2 廠商 = 4 節點
        assert len(result["nodes"]) == 4
        types = {n["type"] for n in result["nodes"]}
        assert types == {"agency", "tender", "company"}

        # 應有 1 發標 + 1 得標 + 1 投標 = 3 邊
        assert len(result["edges"]) == 3
        relations = {e["relation"] for e in result["edges"]}
        assert "發標" in relations
        assert "得標" in relations
        assert "投標" in relations

        assert result["stats"]["tenders"] == 1
        assert result["stats"]["agencies"] == 1
        assert result["stats"]["companies"] == 2

    @pytest.mark.asyncio
    async def test_max_tenders_limit(self, mock_db):
        """超過 max_tenders 限制的標案不應建立節點"""
        from app.services.tender_cache_service import build_graph_from_db
        from datetime import date

        rows = []
        for i in range(5):
            row = MagicMock()
            row.id = i + 1
            row.title = f"標案{i+1}"
            row.unit_name = "機關A"
            row.unit_id = "UA"
            row.job_number = f"J{i+1}"
            row.category = "工程"
            row.announce_date = date(2026, 1, i + 1)
            row.company_name = None
            row.role = None
            rows.append(row)

        mock_db.execute.return_value = _fetchall_result(rows)
        result = await build_graph_from_db(mock_db, "標案", max_tenders=3)

        # 限制 3 筆標案
        assert result["stats"]["tenders"] == 3


class TestCrossReferencePmCases:
    """cross_reference_pm_cases 跨服務索引測試"""

    @pytest.mark.asyncio
    async def test_no_matches_returns_zero(self, mock_db):
        """無匹配時應回傳 linked=0"""
        from app.services.tender_cache_service import cross_reference_pm_cases

        mock_db.execute.return_value = _fetchall_result([])
        result = await cross_reference_pm_cases(mock_db)
        assert result["linked"] == 0

    @pytest.mark.asyncio
    async def test_matches_return_linked_count(self, mock_db):
        """有匹配時應回傳正確的 linked 數量和 case_code"""
        from app.services.tender_cache_service import cross_reference_pm_cases

        linked_rows = [
            (1, "水利工程設計", "CASE-2026-001"),
            (2, "道路養護案", "CASE-2026-002"),
        ]
        mock_db.execute.return_value = _fetchall_result(linked_rows)
        result = await cross_reference_pm_cases(mock_db)

        assert result["linked"] == 2
        assert len(result["cases"]) == 2
        assert result["cases"][0]["case_code"] == "CASE-2026-001"

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, mock_db):
        """異常時應回傳 error 且 linked=0"""
        from app.services.tender_cache_service import cross_reference_pm_cases

        mock_db.execute.side_effect = Exception("DB error")
        result = await cross_reference_pm_cases(mock_db)
        assert result["linked"] == 0
        assert "error" in result


class TestNormalizeCompanyNames:
    """normalize_company_names 廠商名稱正規化測試"""

    @pytest.mark.asyncio
    async def test_no_duplicates(self, mock_db):
        """無重複時 potential_duplicates 應為空"""
        from app.services.tender_cache_service import normalize_company_names

        companies = [("甲公司", 5), ("乙公司", 3), ("丙公司", 2)]
        mock_db.execute.return_value = _fetchall_result(companies)
        result = await normalize_company_names(mock_db)

        assert result["total_companies"] == 3
        assert result["potential_duplicates"] == []

    @pytest.mark.asyncio
    async def test_detects_prefix_duplicates(self, mock_db):
        """前4字相同的廠商應被偵測為疑似重複"""
        from app.services.tender_cache_service import normalize_company_names

        companies = [
            ("乾坤工程顧問有限公司", 10),
            ("乾坤工程顧問股份有限公司", 5),
            ("其他公司名稱很長", 3),
        ]
        mock_db.execute.return_value = _fetchall_result(companies)
        result = await normalize_company_names(mock_db)

        assert result["total_companies"] == 3
        assert len(result["potential_duplicates"]) == 1
        dup = result["potential_duplicates"][0]
        assert dup["prefix"] == "乾坤工程"
        assert len(dup["variants"]) == 2

    @pytest.mark.asyncio
    async def test_short_names_excluded(self, mock_db):
        """長度 < 4 的廠商名稱不參與前綴比對"""
        from app.services.tender_cache_service import normalize_company_names

        companies = [("甲乙丙", 5), ("甲乙丁", 3)]  # len < 4
        mock_db.execute.return_value = _fetchall_result(companies)
        result = await normalize_company_names(mock_db)

        assert result["potential_duplicates"] == []


class TestRefreshPendingTenders:
    """refresh_pending_tenders 待更新標案測試"""

    @pytest.mark.asyncio
    async def test_no_pending_returns_zero(self, mock_db):
        """無待更新標案時應回傳 checked=0, updated=0"""
        from app.services.tender_cache_service import refresh_pending_tenders

        mock_db.execute.return_value = _fetchall_result([])
        result = await refresh_pending_tenders(mock_db)
        assert result == {"checked": 0, "updated": 0}
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_updated_status_committed(self, mock_db):
        """狀態有更新時應 commit"""
        from app.services.tender_cache_service import refresh_pending_tenders

        pending_row = MagicMock()
        pending_row.id = 1
        pending_row.unit_id = "U1"
        pending_row.job_number = "J1"
        pending_row.title = "測試標案"
        pending_row.status = "等標期"

        # 第一次 execute: SELECT pending
        mock_db.execute.side_effect = [
            _fetchall_result([pending_row]),  # SELECT pending
            MagicMock(),                      # UPDATE status
            _fetchall_result([]),             # SELECT existing company_names
        ]

        with patch("app.services.tender_search_service.TenderSearchService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_tender_detail = AsyncMock(return_value={
                "title": "測試標案",
                "latest": {"status": "決標公告"},
                "events": [
                    {"type": "決標公告", "award_details": {"total_award_amount": 5000000}},
                ],
            })

            result = await refresh_pending_tenders(mock_db)
            assert result["checked"] == 1
            assert result["updated"] == 1
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_status_change_no_update(self, mock_db):
        """狀態未變更時不應計入 updated"""
        from app.services.tender_cache_service import refresh_pending_tenders

        pending_row = MagicMock()
        pending_row.id = 2
        pending_row.unit_id = "U2"
        pending_row.job_number = "J2"
        pending_row.title = "測試標案2"
        pending_row.status = "等標期"

        mock_db.execute.return_value = _fetchall_result([pending_row])

        with patch("app.services.tender_search_service.TenderSearchService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_tender_detail = AsyncMock(return_value={
                "title": "測試標案2",
                "latest": {},
                "events": [{"type": "公開招標"}],  # 非決標/廢標
            })

            result = await refresh_pending_tenders(mock_db)
            assert result["checked"] == 1
            assert result["updated"] == 0
