"""
ezbid 爬蟲單元測試

測試 HTML 解析邏輯 (mock HTTP)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.ezbid_scraper import EzbidScraper


SAMPLE_HTML = """
<html><body>
<a href="/tender/12345?source=" class="card-link">
  <div>公告</div>
  <div>剩 7 天</div>
  <div>115年度測量計畫委託服務</div>
  <div>勞務類</div>
  <div>115/04/07</div>
  <div>交通部公路局</div>
  <div>$</div>
  <div>3,960,601</div>
</a>
<a href="/tender/12346?source=" class="card-link">
  <div>已截止</div>
  <div>已截止</div>
  <div>114年度地籍測量案</div>
  <div>工程類</div>
  <div>114/12/15</div>
  <div>內政部</div>
  <div>$</div>
  <div>5,000,000</div>
</a>
</body></html>
"""


class TestEzbidParser:
    """HTML 解析測試"""

    def test_parse_html_extracts_records(self):
        scraper = EzbidScraper()
        records = scraper._parse_html(SAMPLE_HTML)
        assert len(records) == 2

    def test_parse_html_first_record_fields(self):
        scraper = EzbidScraper()
        records = scraper._parse_html(SAMPLE_HTML)
        r = records[0]
        assert r["ezbid_id"] == "12345"
        assert r["title"] == "115年度測量計畫委託服務"
        assert r["category"] == "勞務"
        assert r["date"] == "2026-04-07"
        assert r["unit_name"] == "交通部公路局"
        assert r["budget"] == 3960601
        assert r["days_left"] == 7
        assert r["status"] == "公告"

    def test_parse_html_closed_record(self):
        scraper = EzbidScraper()
        records = scraper._parse_html(SAMPLE_HTML)
        r = records[1]
        assert r["ezbid_id"] == "12346"
        assert r["date"] == "2025-12-15"
        assert r["days_left"] == 0
        assert r["budget"] == 5000000

    def test_parse_html_empty(self):
        scraper = EzbidScraper()
        records = scraper._parse_html("<html><body>No tenders</body></html>")
        assert records == []


class TestRocToDate:
    """ROC 日期轉換測試"""

    def test_roc_to_date_normal(self):
        assert EzbidScraper._roc_to_date("115/04/07") == "2026-04-07"

    def test_roc_to_date_early(self):
        assert EzbidScraper._roc_to_date("100/01/01") == "2011-01-01"

    def test_roc_to_date_invalid(self):
        assert EzbidScraper._roc_to_date("abc") == ""

    def test_roc_to_date_empty(self):
        assert EzbidScraper._roc_to_date("") == ""


class TestParseBudget:

    def test_parse_budget_normal(self):
        assert EzbidScraper._parse_budget("3,960,601") == 3960601

    def test_parse_budget_no_comma(self):
        assert EzbidScraper._parse_budget("5000000") == 5000000

    def test_parse_budget_empty(self):
        assert EzbidScraper._parse_budget("") is None

    def test_parse_budget_text(self):
        assert EzbidScraper._parse_budget("依契約") is None


class TestParseDeadline:

    def test_parse_deadline_days(self):
        assert EzbidScraper._parse_deadline("剩 7 天") == 7

    def test_parse_deadline_closed(self):
        assert EzbidScraper._parse_deadline("已截止") == 0

    def test_parse_deadline_today(self):
        assert EzbidScraper._parse_deadline("今日截止") == 0

    def test_parse_deadline_unknown(self):
        assert EzbidScraper._parse_deadline("公告") is None


class TestFetchLatest:

    @pytest.mark.asyncio
    async def test_fetch_latest_returns_records(self):
        scraper = EzbidScraper()
        with patch("app.services.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = SAMPLE_HTML
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper.fetch_latest(query="測量", pages=1)

        assert result["source"] == "ezbid"
        assert result["total"] == 2
        assert len(result["records"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_latest_http_error(self):
        scraper = EzbidScraper()
        with patch("app.services.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper.fetch_latest(pages=1)

        assert result["total"] == 0
        assert result["records"] == []
