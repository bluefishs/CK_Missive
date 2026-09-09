# -*- coding: utf-8 -*-
"""search 與 keyword 是同一個語意（2026-09-09 晚，篩選模組化第一步）。

同時繼承 BaseQueryParams（search）與 CaseListFilters（keyword）的 Request，送任一個都等於兩個都有；
只有 keyword 的類不受影響。前端 27 處逐頁改名是第二步，這條鎖保證改到一半不會壞。
"""
from app.schemas.erp.quotation import ERPQuotationListRequest
from app.schemas.pm.case import PMCaseListRequest
from app.schemas.erp.vendor_financial import VendorAccountListRequest


def test_keyword_fills_search_on_dual_classes():
    q = ERPQuotationListRequest(keyword="測量")
    assert q.search == "測量" and q.keyword == "測量"
    p = PMCaseListRequest(search="鎮泓")
    assert p.keyword == "鎮泓" and p.search == "鎮泓"


def test_both_given_are_kept_as_is():
    q = ERPQuotationListRequest(search="a", keyword="b")
    assert (q.search, q.keyword) == ("a", "b")


def test_keyword_only_classes_untouched():
    v = VendorAccountListRequest(keyword="x")
    assert v.keyword == "x" and not hasattr(v, "search")


def test_empty_stays_empty():
    q = ERPQuotationListRequest()
    assert q.search is None and q.keyword is None
