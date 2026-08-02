"""
ezbid 爬蟲單元測試

測試 HTML 解析邏輯 (mock HTTP)
"""
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# v6.12 P3 (2026-05-27): 改用新 DDD path (services.tender.*)
from app.services.tender.ezbid_scraper import EzbidScraper, BLOCK_THRESHOLD


# 2026-08-03：原本這裡內嵌一份手寫 SAMPLE_HTML，與 contract test 讀的
# `fixtures/ezbid_sample.html` 是**兩份各自漂移的 fixture**。站台 08-02 改版後
# 兩份都過時，parser 重寫因此完全沒有回歸保護（10 個測試同時紅才被發現）。
# 現在統一讀同一份真實 snapshot，上游改版時只需重錄一次。
SAMPLE_HTML = (
    Path(__file__).parent.parent / "fixtures" / "ezbid_sample.html"
).read_text(encoding="utf-8")


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
        # 改版後 ezbid_id 是 PCC 複合鍵 unit_id/job_number，可直接對應 PCC（ADR-0046）
        assert r["ezbid_id"] == "3.13.52/1154F078"
        assert r["unit_id"] == "3.13.52"
        assert r["job_number"] == "1154F078"
        assert r["title"] == "檢修漏管理資訊系統改版整合案"
        assert r["category"] == "勞務"
        assert r["date"] == "2026-08-03"
        assert r["unit_name"] == "台灣自來水股份有限公司"
        assert r["budget"] == 9474490
        assert r["days_left"] == 11
        assert r["status"] == "公告"

    def test_parse_html_second_record_fields(self):
        """第二筆用不同的 unit_id 形態（4 段）驗證特徵定位不靠固定索引。"""
        scraper = EzbidScraper()
        records = scraper._parse_html(SAMPLE_HTML)
        r = records[1]
        assert r["ezbid_id"] == "3.76.55.20/FI1150728OB"
        assert r["date"] == "2026-08-03"
        assert r["days_left"] == 9
        assert r["budget"] == 3900000

    def test_parse_html_ignores_header_row(self):
        """表頭 <tr> 沒有 /detail/ 連結，不得被當成一筆標案。"""
        scraper = EzbidScraper()
        records = scraper._parse_html(SAMPLE_HTML)
        assert all(r["title"] not in ("標案名稱 / 押標金", "招標機關") for r in records)

    def test_parse_html_rejects_legacy_format(self):
        """舊版 `/tender/{id}` 格式應解析為 0 筆。

        站台 2026-08 已 301 永久搬家並改版，舊格式不會再出現；
        若哪天又解析得出來，代表有人把舊解析路徑加回來了。
        """
        legacy = (
            '<html><body><a href="/tender/12345" class="card-link">'
            "<div>公告</div><div>剩 7 天</div><div>某測量案</div></a></body></html>"
        )
        assert EzbidScraper()._parse_html(legacy) == []

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
        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
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
        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper.fetch_latest(pages=1)

        assert result["total"] == 0
        assert result["records"] == []


# ============================================================================
# 封鎖偵測 + health status（P1-3 補強，2026-05-27）
# ============================================================================

class TestEzbidBlockDetection:
    """L29 family 治理：封鎖偵測與 BLOCK_THRESHOLD 早報警邏輯"""

    def test_health_starts_healthy(self):
        scraper = EzbidScraper()
        status = scraper.get_health_status()
        assert status["healthy"] is True
        assert status["consecutive_failures"] == 0

    def test_health_unhealthy_at_threshold(self):
        scraper = EzbidScraper()
        scraper._consecutive_failures = BLOCK_THRESHOLD
        status = scraper.get_health_status()
        assert status["healthy"] is False
        assert status["consecutive_failures"] == BLOCK_THRESHOLD

    @pytest.mark.asyncio
    async def test_fetch_page_short_circuits_after_threshold(self):
        """連續失敗達 threshold → _fetch_page 立即 return []，不打網路"""
        scraper = EzbidScraper()
        scraper._consecutive_failures = BLOCK_THRESHOLD
        # 不需 mock httpx — 路徑根本不會走到那
        result = await scraper._fetch_page(None, "ALL", 1, 100)
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_page_increments_failures_on_403(self):
        """HTTP 403 → consecutive_failures + 1，return []"""
        scraper = EzbidScraper()
        assert scraper._consecutive_failures == 0

        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.text = ""
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper._fetch_page(None, "ALL", 1, 100)

        assert result == []
        assert scraper._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_page_detects_captcha_keyword(self):
        """response body 含 'captcha' → consecutive_failures + 1"""
        scraper = EzbidScraper()

        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "Please solve captcha to continue"
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper._fetch_page(None, "ALL", 1, 100)

        assert result == []
        assert scraper._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_bootstrap_css_class_is_not_treated_as_block(self):
        """正常頁面含 `d-inline-block` 等 CSS class，不得被判成封鎖。

        2026-08-03 迴歸：原偵測是 `"block" in body_lower`，會被 Bootstrap 的
        `d-inline-block` / `d-md-block` 命中 → 正常頁面直接 return [] 放棄整批。
        之所以沒天天爆，只因為它僅檢查前 2000 字元、CSS 剛好落在後面 —— 純屬運氣。
        """
        scraper = EzbidScraper()

        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = (
                '<html><head><style>.d-inline-block{display:block}</style></head>'
                "<body>" + SAMPLE_HTML + "</body></html>"
            )
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper._fetch_page(None, "ALL", 1, 100)

        assert scraper._consecutive_failures == 0, "正常頁面不該累計封鎖失敗"
        assert len(result) >= 1, "正常頁面應解析出標案"

    @pytest.mark.asyncio
    async def test_real_block_page_still_detected(self):
        """真的封鎖頁仍要被抓到（確認上面的修法沒把偵測整個關掉）。"""
        scraper = EzbidScraper()

        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<html><body>Access Denied — your IP has been blocked</body></html>"
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper._fetch_page(None, "ALL", 1, 100)

        assert result == []
        assert scraper._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_fetch_page_resets_failures_on_success(self):
        """200 + 正常 HTML → consecutive_failures 歸 0"""
        scraper = EzbidScraper()
        scraper._consecutive_failures = 2

        with patch("app.services.tender.ezbid_scraper.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = SAMPLE_HTML
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_resp)

            result = await scraper._fetch_page(None, "ALL", 1, 100)

        assert len(result) == 2
        assert scraper._consecutive_failures == 0


# ============================================================================
# 快取行為（redis_client=None fallback）
# ============================================================================

class TestEzbidCacheNoRedis:
    """無 Redis 時不應 crash — fail-safe path"""

    @pytest.mark.asyncio
    async def test_get_cache_returns_none_when_no_redis(self):
        scraper = EzbidScraper(redis_client=None)
        result = await scraper._get_cache("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_silent_when_no_redis(self):
        # 不應拋例外
        scraper = EzbidScraper(redis_client=None)
        await scraper._set_cache("test_key", {"foo": "bar"}, ttl=60)
