# -*- coding: utf-8 -*-
"""帳款列表「計畫類別／案件狀態」的聚合判準（2026-09-07）。

這一支鎖的是**兩頁共用一份口徑**這件事本身。純函式部分不打 DB；
SQL 已於當日直接對正式庫跑過（腿 1 與廠商腿各回真實列），這裡鎖的是它周邊
最容易在日後改壞的三件事：

1. 代碼要譯成中文 —— 畫面上出現「02」等於沒有這一欄
2. 同一個標籤要合併計數 —— 兩條腿各回一列時不得變成兩個「執行中」
3. 承攬案狀態優先於 PM 階段狀態 —— 否則同一個案會同時顯示「已承攬」與「執行中」
"""
from __future__ import annotations

from app.repositories.erp.case_profile import (
    CATEGORY_LABELS,
    PM_STATUS_LABELS,
    _PM_STATUS_CASE,
    _blank,
    _finalize,
    _merge,
)


class TestLabelMapping:
    def test_category_codes_are_translated(self):
        assert CATEGORY_LABELS["01"] == "委辦招標"
        assert CATEGORY_LABELS["02"] == "承攬報價"

    def test_pm_status_codes_are_translated(self):
        # 實測 pm_cases.status 只有這三個值；漏一個就會有列顯示英文代碼
        for code in ("planning", "contracted", "closed"):
            assert code in PM_STATUS_LABELS

    def test_sql_case_expression_covers_every_mapped_code(self):
        for code, label in PM_STATUS_LABELS.items():
            assert f"WHEN '{code}' THEN '{label}'" in _PM_STATUS_CASE
        # 沒對到的值原樣輸出，不得變成空字串（那會讓一整群案在狀態欄消失）
        assert "ELSE COALESCE(p.status, '')" in _PM_STATUS_CASE


class TestMerge:
    def test_same_status_from_two_legs_is_summed_not_duplicated(self):
        p = _blank()
        _merge(p, "02", "執行中", 3)   # 腿 1（PM 案件）
        _merge(p, "02", "執行中", 2)   # 腿 2（PM 沒涵蓋的承攬案）
        assert p["statuses"] == [{"label": "執行中", "count": 5}]
        assert p["categories"] == ["承攬報價"], "同一個類別不得列兩次"

    def test_unknown_category_falls_back_to_raw_value(self):
        p = _blank()
        _merge(p, "99", "執行中", 1)
        assert p["categories"] == ["99"], "未知代碼要看得見，不能靜靜消失"

    def test_empty_values_are_dropped(self):
        p = _blank()
        _merge(p, None, None, 1)
        _merge(p, "  ", "", 1)
        assert p == {"categories": [], "statuses": []}

    def test_statuses_sorted_by_count_desc(self):
        p = _blank()
        _merge(p, "02", "已結案", 1)
        _merge(p, "02", "執行中", 4)
        _finalize({"k": p})
        assert [s["label"] for s in p["statuses"]] == ["執行中", "已結案"]
