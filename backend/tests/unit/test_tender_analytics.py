"""
標案分析單元測試

測試 tender_analytics_battle.py 和 tender_analytics_price.py：
- battle_room: 戰情室去重 + 競爭對手統計 + cap at 8
- org_ecosystem: 機關生態 (年度趨勢 + Top 廠商 + 類別)
- price_analysis: 底價分析 (預算/底價/決標金額)
- price_trends: 價格趨勢 (統計分布)
- company_profile: 廠商得標分析 (勝率 + 年度趨勢)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_search_service():
    """建立 mock TenderSearchService"""
    svc = MagicMock()
    svc.get_tender_detail = AsyncMock()
    svc.search_by_title = AsyncMock()
    svc.search_by_org = AsyncMock()
    svc.search_by_company = AsyncMock()
    return svc


def _make_record(title="測試標案", job_number="J001", unit_name="測試機關",
                 unit_id="U1", date="2026-04-01", raw_date=20260401,
                 category="工程", type_="公開招標", budget="1000000",
                 winner_names=None, bidder_names=None):
    """建立標準標案記錄 dict"""
    return {
        "title": title, "job_number": job_number, "unit_name": unit_name,
        "unit_id": unit_id, "date": date, "raw_date": raw_date,
        "category": category, "type": type_, "budget": budget,
        "winner_names": winner_names or [], "bidder_names": bidder_names or [],
    }


class TestBattleRoom:
    """battle_room 投標戰情室測試"""

    @pytest.mark.asyncio
    async def test_detail_not_found_returns_error(self):
        """標案不存在時應回傳 error"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        svc.get_tender_detail.return_value = None

        result = await battle_room(svc, "U1", "J1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_similar_and_competitors(self):
        """應回傳 similar_tenders 和 competitors"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        detail = {
            "title": "水利工程設計監造服務",
            "latest": {"agency_name": "水利署", "budget": "5000000"},
        }

        similar_records = [
            _make_record(title="水利工程設計A", job_number="JA",
                         winner_names=["公司甲"], bidder_names=["公司乙"]),
            _make_record(title="水利工程設計B", job_number="JB",
                         winner_names=["公司甲"]),
        ]
        svc.search_by_title.return_value = {"records": similar_records}

        result = await battle_room(svc, "U1", "J1", detail=detail)

        assert "similar_tenders" in result
        assert "competitors" in result
        assert result["tender"]["title"] == "水利工程設計監造服務"

    @pytest.mark.asyncio
    async def test_dedup_by_job_number(self):
        """相同 job_number 的標案應被去重"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        detail = {"title": "測試標案", "latest": {}}

        # 3 records but J1 duplicated
        similar_records = [
            _make_record(job_number="JA"),
            _make_record(job_number="JA"),  # duplicate
            _make_record(job_number="JB"),
        ]
        svc.search_by_title.return_value = {"records": similar_records}

        result = await battle_room(svc, "U1", "J1", detail=detail)
        assert result["similar_count"] == 2  # JA + JB (deduped)

    @pytest.mark.asyncio
    async def test_self_excluded_from_similar(self):
        """自身標案 (同 job_number) 應從相似標案中排除"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        detail = {"title": "本標案", "latest": {}}

        similar_records = [
            _make_record(job_number="J1"),   # 自己，應排除
            _make_record(job_number="JX"),   # 其他
        ]
        svc.search_by_title.return_value = {"records": similar_records}

        result = await battle_room(svc, "U1", "J1", detail=detail)
        assert result["similar_count"] == 1

    @pytest.mark.asyncio
    async def test_cap_at_8_similar(self):
        """相似標案最多保留 8 筆"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        detail = {"title": "大量標案", "latest": {}}

        similar_records = [
            _make_record(job_number=f"J{i}", winner_names=["公司X"])
            for i in range(15)
        ]
        svc.search_by_title.return_value = {"records": similar_records}

        result = await battle_room(svc, "U1", "JSELF", detail=detail)
        assert len(result["similar_tenders"]) <= 8

    @pytest.mark.asyncio
    async def test_competitor_win_rate_calculation(self):
        """競爭對手勝率應正確計算"""
        from app.services.tender_analytics_battle import battle_room

        svc = _make_search_service()
        detail = {"title": "測試", "latest": {"budget": "1000000"}}

        # 公司A: 出現 2 次, 得標 1 次 → 50%
        similar_records = [
            _make_record(job_number="JA", winner_names=["公司A"], bidder_names=["公司B"]),
            _make_record(job_number="JB", winner_names=["公司B"], bidder_names=["公司A"]),
        ]
        svc.search_by_title.return_value = {"records": similar_records}

        result = await battle_room(svc, "U1", "JSELF", detail=detail)

        comp_a = next((c for c in result["competitors"] if c["name"] == "公司A"), None)
        assert comp_a is not None
        assert comp_a["appear_count"] == 2
        assert comp_a["win_count"] == 1
        assert comp_a["win_rate"] == 50.0


class TestOrgEcosystem:
    """org_ecosystem 機關生態測試"""

    @pytest.mark.asyncio
    async def test_no_records_returns_total_zero(self):
        """無記錄時應回傳 total=0"""
        from app.services.tender_analytics_battle import org_ecosystem

        svc = _make_search_service()
        svc.search_by_org.return_value = {"records": []}
        svc.search_by_title.return_value = {"records": []}

        result = await org_ecosystem(svc, "不存在的機關", pages=1)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_year_trend_and_vendors(self):
        """應回傳年度趨勢和 Top 廠商"""
        from app.services.tender_analytics_battle import org_ecosystem

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", raw_date=20250101, winner_names=["甲公司"]),
            _make_record(job_number="J2", raw_date=20260301, winner_names=["甲公司"]),
            _make_record(job_number="J3", raw_date=20260401, winner_names=["乙公司"],
                         bidder_names=["甲公司"]),
        ]
        svc.search_by_org.return_value = {"records": records}
        svc.search_by_title.return_value = {"records": []}

        result = await org_ecosystem(svc, "水利署", pages=1)

        assert result["total"] == 3
        assert len(result["year_trend"]) >= 1
        assert len(result["top_vendors"]) >= 1

        # 甲公司: appear 3, wins 2
        vendor_a = next((v for v in result["top_vendors"] if v["name"] == "甲公司"), None)
        assert vendor_a is not None
        assert vendor_a["appear_count"] == 3
        assert vendor_a["win_count"] == 2

    @pytest.mark.asyncio
    async def test_dedup_across_pages(self):
        """跨頁結果應以 job_number 去重"""
        from app.services.tender_analytics_battle import org_ecosystem

        svc = _make_search_service()
        page1_records = [_make_record(job_number="J1")]
        page2_records = [_make_record(job_number="J1")]  # same

        svc.search_by_org.return_value = {"records": page1_records}
        svc.search_by_title.return_value = {"records": page2_records}

        result = await org_ecosystem(svc, "機關A", pages=1)
        assert result["total"] == 1  # deduped

    @pytest.mark.asyncio
    async def test_category_distribution(self):
        """應正確統計類別分布"""
        from app.services.tender_analytics_battle import org_ecosystem

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", category="工程"),
            _make_record(job_number="J2", category="工程"),
            _make_record(job_number="J3", category="勞務"),
        ]
        svc.search_by_org.return_value = {"records": records}
        svc.search_by_title.return_value = {"records": []}

        result = await org_ecosystem(svc, "機關B", pages=1)
        cats = {c["name"]: c["value"] for c in result["category_distribution"]}
        assert cats.get("工程") == 2
        assert cats.get("勞務") == 1


class TestPriceAnalysis:
    """price_analysis 底價分析測試"""

    @pytest.mark.asyncio
    async def test_detail_not_found_returns_error(self):
        """標案不存在時回傳 error"""
        from app.services.tender_analytics_price import price_analysis

        svc = _make_search_service()
        svc.get_tender_detail.return_value = None

        result = await price_analysis(svc, "U1", "J1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_prices_and_analysis(self):
        """應回傳 prices + analysis 含變異百分比"""
        from app.services.tender_analytics_price import price_analysis

        svc = _make_search_service()
        detail = {
            "title": "測試標案",
            "unit_name": "機關A",
            "events": [{
                "type": "決標公告",
                "detail": {"budget": "10,000,000"},
                "award_details": {
                    "floor_price": 9000000,
                    "total_award_amount": 8500000,
                    "award_date": "2026-04-01",
                    "award_items": [{"item": "工程", "amount": 8500000}],
                },
            }],
        }

        result = await price_analysis(svc, "U1", "J1", detail=detail)

        assert result["prices"]["budget"] == 10000000.0
        assert result["prices"]["floor_price"] == 9000000
        assert result["prices"]["award_amount"] == 8500000
        assert "budget_award_variance_pct" in result["analysis"]
        assert "floor_award_variance_pct" in result["analysis"]
        assert "savings_rate_pct" in result["analysis"]

    @pytest.mark.asyncio
    async def test_missing_prices_no_analysis(self):
        """缺少價格資訊時 analysis 應為空"""
        from app.services.tender_analytics_price import price_analysis

        svc = _make_search_service()
        detail = {
            "title": "只有標題", "unit_name": "機關",
            "events": [{"type": "公開招標", "detail": {}}],
        }

        result = await price_analysis(svc, "U1", "J1", detail=detail)
        assert result["analysis"] == {}
        assert result["prices"]["budget"] is None


class TestPriceTrends:
    """price_trends 價格趨勢測試"""

    @pytest.mark.asyncio
    async def test_no_records_returns_zero_total(self):
        """無記錄時 total=0"""
        from app.services.tender_analytics_price import price_trends

        svc = _make_search_service()
        svc.search_by_title.return_value = {"records": []}

        result = await price_trends(svc, "不存在")
        assert result["total"] == 0
        assert result["stats"]["budget"]["count"] == 0

    @pytest.mark.asyncio
    async def test_aggregation_statistics(self):
        """應正確計算預算統計 (min/max/avg/median)"""
        from app.services.tender_analytics_price import price_trends

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", unit_id="U1"),
            _make_record(job_number="J2", unit_id="U2"),
        ]
        svc.search_by_title.return_value = {"records": records}

        # 兩個 detail 有預算
        svc.get_tender_detail.side_effect = [
            {
                "events": [{"type": "公開招標", "detail": {"budget": "5,000,000"}}],
            },
            {
                "events": [{"type": "公開招標", "detail": {"budget": "10,000,000"}}],
            },
        ]

        result = await price_trends(svc, "工程", pages=1)
        assert result["total"] == 2
        assert result["stats"]["budget"]["count"] == 2
        assert result["stats"]["budget"]["min"] == 5000000.0
        assert result["stats"]["budget"]["max"] == 10000000.0

    @pytest.mark.asyncio
    async def test_distribution_ranges(self):
        """應正確分類預算範圍"""
        from app.services.tender_analytics_price import price_trends

        svc = _make_search_service()
        records = [_make_record(job_number="J1", unit_id="U1")]
        svc.search_by_title.return_value = {"records": records}
        svc.get_tender_detail.return_value = {
            "events": [{"type": "x", "detail": {"budget": "800,000"}}],
        }

        result = await price_trends(svc, "小案", pages=1)
        ranges = {d["range"]: d["count"] for d in result["distribution"]}
        assert ranges.get("100萬以下") == 1


class TestCompanyProfile:
    """company_profile 廠商分析測試"""

    @pytest.mark.asyncio
    async def test_no_records_returns_total_zero(self):
        """無記錄時 total=0"""
        from app.services.tender_analytics_price import company_profile

        svc = _make_search_service()
        svc.search_by_company.return_value = {"records": []}

        result = await company_profile(svc, "不存在公司")
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_win_rate_calculation(self):
        """勝率應正確計算 (含部分名稱匹配)"""
        from app.services.tender_analytics_price import company_profile

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", winner_names=["乾坤工程顧問有限公司"]),
            _make_record(job_number="J2", winner_names=["其他公司"]),
            _make_record(job_number="J3", winner_names=["乾坤工程"]),
        ]
        # pages=1 避免多頁重複
        svc.search_by_company.side_effect = [
            {"records": records},
            {"records": []},  # page 2 empty → stops
        ]

        result = await company_profile(svc, "乾坤工程", pages=1)

        assert result["total"] == 3
        # "乾坤工程" in "乾坤工程顧問有限公司" → True, "乾坤工程" in "其他公司" → False
        # "乾坤工程" in "乾坤工程" → True
        assert result["won_count"] == 2
        assert result["win_rate"] == pytest.approx(66.7, abs=0.1)

    @pytest.mark.asyncio
    async def test_year_trend_sorted(self):
        """年度趨勢應按年份排序"""
        from app.services.tender_analytics_price import company_profile

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", raw_date=20260101),
            _make_record(job_number="J2", raw_date=20250601),
            _make_record(job_number="J3", raw_date=20260401),
        ]
        svc.search_by_company.return_value = {"records": records}

        result = await company_profile(svc, "公司A")
        years = [t["year"] for t in result["year_trend"]]
        assert years == sorted(years)

    @pytest.mark.asyncio
    async def test_top_agencies(self):
        """應統計 Top 機關分布"""
        from app.services.tender_analytics_price import company_profile

        svc = _make_search_service()
        records = [
            _make_record(job_number="J1", unit_name="水利署"),
            _make_record(job_number="J2", unit_name="水利署"),
            _make_record(job_number="J3", unit_name="交通部"),
        ]
        svc.search_by_company.side_effect = [
            {"records": records},
            {"records": []},
        ]

        result = await company_profile(svc, "公司B", pages=1)
        agencies = {a["name"]: a["count"] for a in result["top_agencies"]}
        assert agencies["水利署"] == 2
        assert agencies["交通部"] == 1

    @pytest.mark.asyncio
    async def test_recent_tenders_limited(self):
        """recent_tenders 最多 20 筆"""
        from app.services.tender_analytics_price import company_profile

        svc = _make_search_service()
        records = [_make_record(job_number=f"J{i}") for i in range(30)]
        svc.search_by_company.return_value = {"records": records}

        result = await company_profile(svc, "公司C")
        assert len(result["recent_tenders"]) <= 20


class TestSafeParseAmount:
    """_safe_parse_amount 輔助函數測試"""

    def test_none_returns_none(self):
        from app.services.tender_analytics_price import _safe_parse_amount
        assert _safe_parse_amount(None) is None

    def test_comma_separated(self):
        from app.services.tender_analytics_price import _safe_parse_amount
        assert _safe_parse_amount("1,000,000") == 1000000.0

    def test_plain_integer(self):
        from app.services.tender_analytics_price import _safe_parse_amount
        assert _safe_parse_amount(5000000) == 5000000.0

    def test_empty_string_returns_none(self):
        from app.services.tender_analytics_price import _safe_parse_amount
        assert _safe_parse_amount("") is None
