# -*- coding: utf-8 -*-
"""ezbid.tw 爬蟲 contract test

目的：固化 ezbid 上游 HTML 結構解析合約。
上游 DOM 改版 → fixtures/ezbid_sample.html 需重新錄製後再更新此測試。

覆蓋：
- _parse_html 產出欄位完整性（schema contract）
- ROC 日期 → 西元轉換
- 預算逗號解析
- 類別標籤去「類」後綴
- 截止天數正則擷取
- 異常資料容錯（部分標案缺欄位不應炸整批）
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.ezbid_scraper import EzbidScraper

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "ezbid_sample.html"

EXPECTED_FIELDS = {
    "ezbid_id", "title", "date", "unit_name", "category",
    "type", "status", "budget", "days_left", "deadline_text",
    "ezbid_url", "source",
}


@pytest.fixture
def sample_html() -> str:
    assert FIXTURE_PATH.exists(), f"Fixture missing: {FIXTURE_PATH}"
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def scraper() -> EzbidScraper:
    return EzbidScraper(redis_client=None)


class TestEzbidParseContract:

    def test_schema_all_records_have_required_fields(self, scraper, sample_html):
        """所有 record 必須包含完整欄位集合（schema contract）。"""
        records = scraper._parse_html(sample_html)
        assert len(records) >= 1, "fixture 至少應有 1 筆 tender"
        for rec in records:
            missing = EXPECTED_FIELDS - set(rec.keys())
            assert not missing, f"record 缺少欄位: {missing} in {rec}"

    def test_source_is_ezbid(self, scraper, sample_html):
        """source 標記固定 ezbid 供下游區分來源。"""
        records = scraper._parse_html(sample_html)
        assert all(r["source"] == "ezbid" for r in records)

    # 2026-08-03：以下三項原本硬編了特定 snapshot 的值（cf.ezbid.tw 網域、
    # 2026-04-16、12,000,000、工程類），使得每次重錄 fixture 都要連帶改斷言，
    # 也讓「站台改版」與「換了一批標案」看起來一樣紅。
    # contract test 要驗的是**結構契約**，改為驗格式。

    def test_ezbid_url_pattern(self, scraper, sample_html):
        """URL 規則：https://ezbid.tw/detail/{unit_id}/{job_number}。"""
        records = scraper._parse_html(sample_html)
        for r in records:
            assert re.fullmatch(
                r"https://ezbid\.tw/detail/[^/]+/[^/]+", r["ezbid_url"]
            ), f"URL 形態不符: {r['ezbid_url']}"
            assert r["ezbid_url"].endswith(r["ezbid_id"])

    def test_roc_date_converted(self, scraper, sample_html):
        """ROC (115/08/03) 應轉為西元 ISO 日期。"""
        records = scraper._parse_html(sample_html)
        dates = [r["date"] for r in records if r["date"]]
        assert dates, "至少一筆應有日期（全空代表日期欄定位失效）"
        for d in dates:
            assert re.fullmatch(r"20\d{2}-\d{2}-\d{2}", d), f"非 ISO 日期: {d}"

    def test_budget_parsed_as_int(self, scraper, sample_html):
        """預算欄位去逗號後為 int（或 None 若缺資料）。"""
        records = scraper._parse_html(sample_html)
        budgets = [r["budget"] for r in records]
        assert all(b is None or isinstance(b, int) for b in budgets)
        assert any(isinstance(b, int) and b > 0 for b in budgets), \
            "全部預算皆缺，代表 '$' 之後的取值失效"

    def test_category_label_strips_lei(self, scraper, sample_html):
        """category 標籤去除「類」字元（勞務類 → 勞務）。"""
        records = scraper._parse_html(sample_html)
        cats = {r["category"] for r in records if r["category"]}
        assert cats, "全部分類皆空，代表分類欄定位失效"
        assert not any(c.endswith("類") for c in cats), \
            f"原始『類』後綴應被 strip: {cats}"

    def test_status_公告_maps_to_type(self, scraper, sample_html):
        """status=公告 → type=公開招標公告；其他 status 原樣保留。"""
        records = scraper._parse_html(sample_html)
        by_status = {r["status"]: r["type"] for r in records}
        assert by_status.get("公告") == "公開招標公告"
        # 決標狀態不轉換
        if "決標" in by_status:
            assert by_status["決標"] == "決標"

    def test_days_left_extracted_when_present(self, scraper, sample_html):
        """deadline_text 含數字時應能解析出 days_left。"""
        records = scraper._parse_html(sample_html)
        for r in records:
            if r["deadline_text"].startswith("剩 "):
                assert isinstance(r["days_left"], int)
                assert r["days_left"] >= 0

    def test_malformed_html_does_not_raise(self, scraper):
        """畸形 HTML 不應拋例外，回空列表或 best-effort。"""
        result = scraper._parse_html("<html><body>no tenders here</body></html>")
        assert result == []

    def test_empty_html_returns_empty_list(self, scraper):
        assert scraper._parse_html("") == []
