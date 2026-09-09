# -*- coding: utf-8 -*-
"""經費指標的判準鎖 —— owner 2026-09-09「統計應建構統一服務端」。

這支測試守的不是「函式會不會執行」，是**口徑本身**：
每個指標的 SQL 片段長什麼樣、認哪些狀態、年度用哪個欄位。

⚠️ 這些斷言故意寫得很死。改口徑時測試會紅，**那正是它的目的** ——
改一個指標會同時改動每一支統計，那必須是刻意的決定，不是順手。
"""
import pytest

from app.services.stats.finance import (
    RECEIVED_STATUSES,
    awarded_amount,
    billed_amount,
    case_year_condition,
    case_year_params,
    paid_amount,
    payable_amount,
    received_amount,
)


class TestAwardedAmount:
    def test_順序是議價_契約_報價總價(self):
        sql = awarded_amount()
        # 三層的先後順序就是口徑本身，換順序會換掉每一張統計卡的數字
        assert sql.index("winning_amount") < sql.index("contract_amount") < sql.index("total_price")

    def test_議價欄用_NULLIF_而不是直接取(self):
        # 議價欄未填時是 0 不是 NULL；少了 NULLIF 會讓「沒議價」被當成「議價 0 元」
        assert "NULLIF(c.winning_amount, 0)" in awarded_amount()

    def test_可換_alias(self):
        assert "x.winning_amount" in awarded_amount(c="x")
        assert "y.total_price" in awarded_amount(q="y")


class TestReceived:
    def test_只認_paid_與_partial(self):
        assert RECEIVED_STATUSES == ("paid", "partial")

    def test_已收款帶狀態條件而已請款不帶(self):
        # 這是 2026-09-09 盤點時三份實作分歧的那一點：
        # 一處有狀態條件、兩處沒有，而當時資料剛好全是 paid ⇒ 數字一致、看不出來
        assert "payment_status IN" in received_amount()
        assert "payment_status" not in billed_amount()

    def test_已付也帶狀態條件(self):
        # 2026-09-09 收斂：三份實作一份 `= 'paid'`、一份無條件，統一到與已收款同一組。
        # 實測當下不改變數字（36 筆有已付金額的狀態全是 paid）。
        assert "payment_status IN" in paid_amount()

    def test_ref_可換成_bind_參數(self):
        # 消費端有兩種形狀：join 了報價單用 `q.id`，只有參數時用 `:qid`
        assert "erp_quotation_id = :qid" in received_amount(ref=":qid")

    def test_金額欄位沒有互相寫錯(self):
        assert "SUM(b.payment_amount)" in received_amount()
        assert "SUM(b.billing_amount)" in billed_amount()
        assert "SUM(p.payable_amount)" in payable_amount()
        assert "SUM(p.paid_amount)" in paid_amount()

    @pytest.mark.parametrize("fn", [billed_amount, received_amount, payable_amount, paid_amount])
    def test_一律_COALESCE_到_0(self, fn):
        # 沒有請款的案子子查詢回 NULL，未包 COALESCE 會讓整列的合計變成 NULL
        assert fn().startswith("COALESCE(")
        assert fn().rstrip().endswith(", 0)")


class TestCaseYear:
    def test_year_欄優先案號年只是後備(self):
        sql = case_year_condition(2026)
        assert "c.year = :yr_i" in sql
        # 後備條件必須綁在 year IS NULL 上，否則就變成兩個口徑並聯
        assert "c.year IS NULL AND q.case_code LIKE :yr" in sql

    def test_參數與條件必須配得起來(self):
        sql = case_year_condition(2026, param="y2")
        p = case_year_params(2026, param="y2")
        assert ":y2_i" in sql and ":y2" in sql
        assert p == {"y2_i": 2026, "y2": "CK2026_%"}

    def test_案號後備用的是前綴比對(self):
        # `CK2026_%` 而不是 `%2026%` —— 後者會命中案名或流水號裡的 2026
        assert case_year_params(2026)["yr"] == "CK2026_%"
