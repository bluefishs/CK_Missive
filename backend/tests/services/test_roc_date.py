"""ROC 日期解析 SSOT regression（2026-06-11，架構標準化）

services/common/roc_date 為全專案民國日期/時間解析唯一來源（收斂 parse_date×10 競爭）。
"""
from datetime import date, datetime

from app.services.common.roc_date import roc_to_ad, parse_roc_date, parse_roc_datetime


class TestRocToAd:
    def test_roc_year(self):
        assert roc_to_ad(112) == 2023

    def test_already_ad(self):
        assert roc_to_ad(2024) == 2024


class TestParseRocDate:
    def test_dotted(self):
        assert parse_roc_date("訂於112.9.21辦理") == date(2023, 9, 21)

    def test_cjk(self):
        assert parse_roc_date("112年9月21日(星期四)") == date(2023, 9, 21)

    def test_none_when_absent(self):
        assert parse_roc_date("無日期文字") is None

    def test_invalid_month(self):
        assert parse_roc_date("112.13.40") is None


class TestParseRocDatetime:
    def test_afternoon(self):
        assert parse_roc_datetime("會議112.11.16(四)下午2時") == datetime(2023, 11, 16, 14, 0)

    def test_am_with_minute(self):
        assert parse_roc_datetime("112.9.22(五)上午9時30分") == datetime(2023, 9, 22, 9, 30)

    def test_noon_am_edge(self):
        assert parse_roc_datetime("113.5.6 上午12時") == datetime(2024, 5, 6, 0, 0)

    def test_date_only_returns_none(self):
        # 只有日期、無時段 → None（呼叫端維持全天）
        assert parse_roc_datetime("訂於112.9.21辦理") is None

    def test_no_date_returns_none(self):
        assert parse_roc_datetime("取得會議(第4場)") is None
