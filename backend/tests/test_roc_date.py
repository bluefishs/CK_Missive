# -*- coding: utf-8 -*-
"""`app.core.roc_date` 必須吃下原本 8 份實作各自吃的格式（A119，2026-09-08）。

每一組樣本都來自被收掉的那一份實作的 docstring 或實際資料；少一組就是回歸。
"""
from datetime import date, datetime

import pytest

from app.core.roc_date import parse_roc_date, roc_to_iso


@pytest.mark.parametrize("raw, expected", [
    # 派工／驗證器：嵌在句子裡、可帶「中華民國／民國」
    ("請於中華民國114年1月8日前完成", date(2025, 1, 8)),
    ("民國114年1月8日", date(2025, 1, 8)),
    ("114年01月15日", date(2025, 1, 15)),
    ("截止日：115年4月7日（含）", date(2026, 4, 7)),
    # 晨報／爬蟲：斜線
    ("115/04/17", date(2026, 4, 17)),
    ("115/4/7", date(2026, 4, 7)),
    # 報價單總表：點分隔，同一欄混有西元
    ("114.02.03", date(2025, 2, 3)),
    ("2025.02.03", date(2025, 2, 3)),
    ("2025-02-03", date(2025, 2, 3)),
    # 財政部：7 位無分隔
    ("1140108", date(2025, 1, 8)),
    ("114/01/08", date(2025, 1, 8)),
    # Excel 原生
    (date(2026, 9, 8), date(2026, 9, 8)),
    (datetime(2026, 9, 8, 10, 0), date(2026, 9, 8)),
])
def test_parse_all_legacy_formats(raw, expected):
    assert parse_roc_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "無", "115年13月40日", "abc", "12345"])
def test_unparsable_returns_none(raw):
    assert parse_roc_date(raw) is None


def test_roc_to_iso_contract():
    # 爬蟲既有契約：成功回 YYYY-MM-DD，失敗回空字串
    assert roc_to_iso("115/04/07") == "2026-04-07"
    assert roc_to_iso("垃圾") == ""


def test_legacy_names_delegate():
    """8 個舊名字仍在，且結果與唯一定義一致（呼叫端沒改）。"""
    from app.services.erp.quotation_legacy_import import _roc_to_date as q
    from app.services.ai.domain.dispatch_progress_synthesizer import _parse_roc_date as d
    from app.services.tender.ezbid_scraper import EzbidScraper
    assert q("114.02.03") == date(2025, 2, 3)
    assert d("截止 114年1月8日") == date(2025, 1, 8)
    assert EzbidScraper._roc_to_date("115/04/07") == "2026-04-07"
