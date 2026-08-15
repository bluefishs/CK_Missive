"""報價的估列費用、實際成本、毛利必須區分清楚。

2026-08-15 owner：「報價單估列費用 實際成本 毛利 皆由區分清楚不可混淆」。

當日查證到三件混淆：
① 成本用的是**報價估列**不是實際支出，而 UI 只寫「估計成本」；
② 成本四欄未填時後端 schema 存成 0，「沒填」與「真的是零」分不出來 ——
   77 筆報價有 37 筆落在這裡，毛利率顯示 100%，最大一筆收入 943 萬；
③ `net_profit` 與 `gross_profit` 是**同一個數字**，而詳情頁把
   「毛利」與「淨利」並排顯示。
"""
from decimal import Decimal

from app.services.erp.quotation_service import compute_quotation_profit


def test_cost_declared_false_when_no_cost_entered():
    """四欄都是 0 → 無法判斷是「沒填」還是「真的零」，必須標出來。"""
    r = compute_quotation_profit(total_price=9435000, tax_amount=0)
    assert r["cost_declared"] is False
    # 數字仍會算出來（相容既有消費端），但 UI 依 cost_declared 決定要不要顯示
    assert r["gross_margin"] == Decimal("100.00")


def test_cost_declared_true_when_any_cost_entered():
    r = compute_quotation_profit(total_price=95000, outsourcing_fee=39950)
    assert r["cost_declared"] is True
    assert r["total_cost"] == Decimal("39950")


def test_net_profit_is_not_a_separate_metric():
    """net_profit 目前就是 gross_profit —— 鎖住這個事實，避免有人以為它是淨利。

    若哪天真的實作了淨利（扣營運費用與稅），這條會紅，
    那時要一併確認 UI 有沒有把兩者當成不同指標呈現。
    """
    r = compute_quotation_profit(total_price=100000, tax_amount=5000,
                                 personnel_fee=30000)
    assert r["net_profit"] == r["gross_profit"], (
        "net_profit 與 gross_profit 不再相等 —— 請確認 UI 的標籤與說明是否同步"
    )


def test_zero_revenue_does_not_fabricate_a_margin():
    """收入為 0 時不得算出毛利率（除以零）。"""
    r = compute_quotation_profit(total_price=0)
    assert r["gross_margin"] is None
