"""線上報價明細 —— 服務層行為鎖定。

2026-08-26 owner：「線上報價單是否已完成前後端服務串接與測試作業」。
答案是串接完成、**測試是零** —— 而零測試讓一個算術上就錯的 bug
活到今天：明細更新後 `total_price` 重算了，`tax_amount` 沒有，
於是 `detail` 回傳「新小計 ＋ 舊稅額」（實測 8,000 + 12,656 = 20,656）。

它沒有真實發生過，因為 `erp_quotation_items` 是 **0 筆 / 256 張報價單**。
⇒ **沒有人用的功能，壞了也不會有人知道** —— 所以要用測試鎖住，
   而不是等使用者踩到。

這一份鎖的是四個實測確認過的行為，每一個都是**曾經或可能出錯**的地方：
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.erp.quotation_items import QuotationItemService


def _svc_with(quotation):
    """建一個 service：`db.execute` 依查詢型態回不同結果。

    service 用兩種方式讀 db：
      * 取報價單  → `(await execute(...)).scalar_one_or_none()`
      * 取既有明細 → `(await execute(...)).scalars().all()`
    ⇒ 同一個 mock 兩種用法都要撐住，否則測試會死在 mock 而不是邏輯上。
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = quotation
    result.scalars.return_value.all.return_value = []   # 既有明細：空

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return QuotationItemService(db), db


def _quotation(total="253120.00", tax="12656.00"):
    q = MagicMock()
    q.id = 390
    q.total_price = Decimal(total)
    q.tax_amount = Decimal(tax)
    return q


@pytest.mark.asyncio
async def test_tax_recalculated_with_subtotal():
    """稅額必須跟著小計走 —— 這是 2026-08-26 修的那個 bug。

    在此之前：小計改成 8,000 而稅額停在 12,656（舊總價的 5%），
    `detail` 就會回 total=20,656。**不需要業務判斷也知道是錯的。**
    """
    q = _quotation()
    svc, _ = _svc_with(q)
    await svc.replace_items(390, [
        {"item_name": "繪製", "qty": 1, "unit": "戶", "unit_price": 4000},
        {"item_name": "簽證", "qty": 2, "unit": "戶", "unit_price": 2000},
    ])
    assert q.total_price == Decimal("8000")
    assert q.tax_amount == Decimal("400"), "稅額應為小計的 5%，而不是沿用舊值"


@pytest.mark.asyncio
async def test_blank_rows_are_skipped():
    """空白列要被略過 —— 表格編輯必然留下空列。

    前端 `InputNumber` 清空時送的是 `0` 不是 `null`
    （`onChange={n => update(k, { qty: n ?? 0 })}`），
    所以空白列長成 `{item_name:'', qty:1, unit_price:0}` ——
    **判斷依據是 item_name 而不是金額**。
    """
    q = _quotation()
    svc, _ = _svc_with(q)
    r = await svc.replace_items(390, [
        {"item_name": "繪製", "qty": 1, "unit": "戶", "unit_price": 4000},
        {"item_name": "", "qty": 1, "unit": "式", "unit_price": 0},
        {"item_name": "   ", "qty": 1, "unit": "式", "unit_price": 0},
    ])
    assert r["item_count"] == 1, "只有一列有工項名"


@pytest.mark.asyncio
async def test_empty_items_do_not_zero_total():
    """清空明細**不得**把總價歸零。

    空明細代表「還沒逐項拆」，不代表「這張報價是 0 元」——
    256 張報價單裡多數只有總價沒有明細，一旦歸零就是資料損毀。
    """
    q = _quotation()
    svc, _ = _svc_with(q)
    r = await svc.replace_items(390, [])
    assert q.total_price == Decimal("253120.00"), "清空明細不得動總價"
    assert q.tax_amount == Decimal("12656.00"), "也不得動稅額"
    assert r["total_price_updated"] is False


@pytest.mark.asyncio
async def test_amount_is_qty_times_unit_price():
    """每列金額 = 數量 × 單價，總計 = 各列金額相加。

    範本（`quotation_template.xlsx` r26）的合計是 `=SUM(F16:F25)`，
    而 F 欄是複價 —— 系統這一側必須算出同樣的東西，
    否則線上填的與印出來的會不一致。
    """
    q = _quotation()
    svc, _ = _svc_with(q)
    r = await svc.replace_items(390, [
        {"item_name": "甲", "qty": 3, "unit_price": 1500},   # 4500
        {"item_name": "乙", "qty": 0.5, "unit_price": 1000},  # 500
    ])
    assert r["items_total"] == 5000.0
    assert q.tax_amount == Decimal("250")
