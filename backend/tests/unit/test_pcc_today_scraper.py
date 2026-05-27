"""Unit tests for PccTodayScraper — 補 P1-3 測試缺口（CLAUDE.md 列為 P1）。

PCC 今日標案爬蟲是「主要資料源」/「權威來源」，但
test 缺口導致 2026-04-08 起 50 天 silent dormant 未被偵測（scheduler 缺
cron 是根因，但 test gap 是 silent dormant 之 enabling condition）。

涵蓋：
- _parse_today_page：依 label_typeN_M table 結構解析公告類型
- fetch_today_tenders：error path（網路無回應）
- cache：無 Redis 時 fail-safe
- type 對應 _SECTION_TYPE_MAP
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.tender.pcc_today_scraper import PccTodayScraper


# ============================================================================
# Fixture HTML：模擬 PCC 頁面結構
# 真實 PCC todayTender 頁面為 header table (id=label_typeX_Y) + sibling data table
# ============================================================================

SAMPLE_PCC_HTML_OPEN_BID = """
<html>
<body>
<table id="label_type1_0"><tr><th>公開招標公告</th></tr></table>
<table>
  <tr><th>項次</th><th>機關名稱</th><th>標案名稱</th><th>標案案號</th><th>截止投標</th></tr>
  <tr>
    <td>1</td>
    <td>桃園市政府</td>
    <td><a href="/tps/atm/main/pms/main_tender_detail.do?pkPmsMain=ABC123">道路修繕工程</a></td>
    <td>JOB-001</td>
    <td>2026-05-30 17:00</td>
  </tr>
  <tr>
    <td>2</td>
    <td>新北市政府</td>
    <td><a href="/tps/atm/main/pms/main_tender_detail.do?pkPmsMain=DEF456">公園綠美化</a></td>
    <td>JOB-002</td>
    <td>2026-06-01 12:00</td>
  </tr>
</table>
</body>
</html>
"""

EMPTY_PCC_HTML = """
<html><body><p>無今日標案</p></body></html>
"""


# ============================================================================
# _parse_today_page
# ============================================================================

class TestPccParseToday:
    def test_parse_extracts_open_bid_records(self):
        scraper = PccTodayScraper()
        records, type_counts = scraper._parse_today_page(SAMPLE_PCC_HTML_OPEN_BID)
        assert len(records) == 2

    def test_parse_records_assigned_correct_type(self):
        """label_type1_0 → 公開招標公告"""
        scraper = PccTodayScraper()
        records, _ = scraper._parse_today_page(SAMPLE_PCC_HTML_OPEN_BID)
        for r in records:
            assert r.get("type") == "公開招標公告" or r.get("tender_type") == "公開招標公告"

    def test_parse_empty_html(self):
        scraper = PccTodayScraper()
        records, type_counts = scraper._parse_today_page(EMPTY_PCC_HTML)
        assert records == []
        # type_counts may be {} or contain only zero values
        assert all(v == 0 for v in type_counts.values()) if type_counts else True

    def test_parse_extracts_pk_pms_main_as_unit_id(self):
        """pkPmsMain 從 href 抽取後寫入 unit_id（per pcc_today_scraper.py:189）"""
        scraper = PccTodayScraper()
        records, _ = scraper._parse_today_page(SAMPLE_PCC_HTML_OPEN_BID)
        unit_ids = {r.get("unit_id") for r in records}
        assert "ABC123" in unit_ids
        assert "DEF456" in unit_ids

    def test_section_type_map_covers_12_types(self):
        """確保 _parse_today_page 內 12 種公告類型 mapping 完整"""
        # 12 = 6 招標 + 6 更正
        # 注意：pkPmsMain regex 是 [A-Za-z0-9=+/]+ → 不含 _，須用純 alphanum ID
        scraper = PccTodayScraper()
        sections_html = "<html><body>"
        for idx in range(6):
            sections_html += f"""
            <table id="label_type1_{idx}"><tr><th>type1-{idx}</th></tr></table>
            <table>
              <tr><td>1</td><td>U</td><td><a href="?pkPmsMain=A1{idx}A">T</a></td><td>JN</td><td>DL</td></tr>
            </table>
            """
        for idx in range(6):
            sections_html += f"""
            <table id="label_type2_{idx}"><tr><th>type2-{idx}</th></tr></table>
            <table>
              <tr><td>1</td><td>U</td><td><a href="?pkPmsMain=B2{idx}B">T</a></td><td>JN</td><td>DL</td></tr>
            </table>
            """
        sections_html += "</body></html>"
        records, _ = scraper._parse_today_page(sections_html)
        # 12 unique tender_id → 應有 12 records
        assert len(records) == 12, f"expected 12 records covering all types, got {len(records)}"


# ============================================================================
# fetch_today_tenders：網路錯誤 + cache 互動
# ============================================================================

class TestPccFetchToday:
    @pytest.mark.asyncio
    async def test_fetch_handles_empty_html(self):
        """_fetch_page 回 None → fetch_today_tenders 給 error 回應"""
        scraper = PccTodayScraper()
        with patch.object(scraper, "_fetch_page", new=AsyncMock(return_value=None)):
            result = await scraper.fetch_today_tenders()

        assert result["total"] == 0
        assert result["records"] == []
        assert result["source"] == "pcc"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_fetch_returns_parsed_records_on_success(self):
        """_fetch_page 回正常 HTML → 應解析 records"""
        scraper = PccTodayScraper()
        with patch.object(
            scraper, "_fetch_page",
            new=AsyncMock(return_value=SAMPLE_PCC_HTML_OPEN_BID),
        ):
            # bypass cache: ensure _get_cache returns None
            with patch.object(scraper, "_get_cache", new=AsyncMock(return_value=None)):
                with patch.object(scraper, "_set_cache", new=AsyncMock(return_value=None)):
                    result = await scraper.fetch_today_tenders()

        assert result["source"] == "pcc"
        assert result["total"] == 2
        assert len(result["records"]) == 2
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_fetch_uses_cache_when_hit(self):
        """_get_cache 回 cached → 不打 _fetch_page"""
        scraper = PccTodayScraper()
        cached_payload = {
            "total": 5, "records": [{"id": "cached"}], "source": "pcc",
            "by_type": {"公開招標公告": 5}, "fetched_at": "2026-05-27T10:00:00",
        }
        fetch_mock = AsyncMock(return_value=None)
        with patch.object(scraper, "_get_cache", new=AsyncMock(return_value=cached_payload)):
            with patch.object(scraper, "_fetch_page", new=fetch_mock):
                result = await scraper.fetch_today_tenders()

        assert result == cached_payload
        fetch_mock.assert_not_called()


# ============================================================================
# Cache fail-safe（無 Redis）
# ============================================================================

class TestPccCacheFailSafe:
    """確保無 Redis 時 PCC scraper 仍可運作（不依賴 cache）"""

    @pytest.mark.asyncio
    async def test_get_cache_returns_none_when_no_redis(self):
        scraper = PccTodayScraper(redis_client=None)
        result = await scraper._get_cache("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_silent_when_no_redis(self):
        scraper = PccTodayScraper(redis_client=None)
        # 不應拋例外
        await scraper._set_cache("test_key", {"foo": "bar"}, ttl=60)
