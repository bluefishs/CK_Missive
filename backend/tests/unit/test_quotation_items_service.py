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


def _quotation(total="253120.00", tax="12656.00", tax_included=False):
    q = MagicMock()
    q.id = 390
    q.total_price = Decimal(total)
    q.tax_amount = Decimal(tax)
    # ⚠️ 2026-09-08：`tax_included` **必須明確設值**。MagicMock 的任何屬性都是
    # truthy 物件 ⇒ 不設就等於「這張已含稅」，於是小計不再 ×1.05、稅額變 0，
    # 而兩支既有測試會以「總價 8,000／稅 0」失敗。今天第二次踩到同一個形狀
    # （PM 案刪除閘門那支的 `project_code` 也是）。
    q.tax_included = tax_included
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
    # 2026-09-06：total_price 依 FIELD_SEMANTICS 是含稅（小計 8,000 × 1.05）；稅額仍是小計的 5%
    assert q.total_price == Decimal("8400")
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


@pytest.mark.asyncio
async def test_tax_included_means_subtotal_is_the_total():
    """⭐ 2026-09-08 owner：「其小記已含稅，故報價單需增列勾選『總價是否含稅』」。

    勾了之後：**小計即總價、稅額不另計**。不分流的話含稅的小計會被再加一次 5%，
    而畫面上三個數字彼此自洽、看不出錯。
    """
    q = _quotation(total="8400.00", tax="400.00", tax_included=True)
    svc, _ = _svc_with(q)
    await svc.replace_items(390, [{"item_name": "測量", "qty": 1, "unit": "式", "unit_price": 8000}])
    assert q.total_price == Decimal("8000"), "含稅時小計即總價，不得再 ×1.05"
    assert q.tax_amount == Decimal("0"), "含稅時稅額不另計"


@pytest.mark.asyncio
async def test_tax_not_included_still_grosses_up():
    """負向對照：沒勾的照舊 ×1.05 —— 修法不得把原本正確的那條路一起改掉。"""
    q = _quotation(total="8400.00", tax="400.00", tax_included=False)
    svc, _ = _svc_with(q)
    await svc.replace_items(390, [{"item_name": "測量", "qty": 1, "unit": "式", "unit_price": 8000}])
    assert q.total_price == Decimal("8400")
    assert q.tax_amount == Decimal("400")


@pytest.mark.asyncio
async def test_recompute_totals_does_nothing_without_items():
    """沒有工項就不動總價 —— 空明細代表「尚未逐項拆」，不是 0 元。

    這一條是 `recompute_totals` 最危險的分支：切換「稅內含」時若把
    沒有明細的報價單算成 0，總價會**歸零而不報錯**，
    而請款、發票、承攬金額全都對著那個數字。
    """
    q = _quotation(total="253120.00", tax="12656.00", tax_included=False)
    svc, _db = _svc_with(q)                      # `_svc_with` 的既有明細＝空

    out = await svc.recompute_totals(390)

    assert out["recomputed"] is False
    assert out["item_count"] == 0
    assert q.total_price == Decimal("253120.00"), "沒有明細時總價不得被動到"
    assert q.tax_amount == Decimal("12656.00")


@pytest.mark.asyncio
async def test_recompute_totals_applies_the_tax_included_rule():
    """切換「稅內含」後，總價要照新規則重算 —— 而且用的是同一份算式。

    ⭐ 2026-09-08 owner：「總價是否含稅，前端也須同步建立管控填報機制，
    以利前後端經費統計」。旗標可以在畫面上切，切了若不重算，
    `total_price` 會停在舊的 ×1.05 而明細分頁說「小計即為總價」——
    **兩個數字各自看都合理**，差異只在跨頁比總額時才浮出來。
    """
    q = _quotation(total="105000.00", tax="5000.00", tax_included=True)
    svc, db = _svc_with(q)

    item = MagicMock()
    item.amount = Decimal("100000.00")
    # 這一支讀既有明細走 `scalars().all()`（同 `list_items`）
    db.execute.return_value.scalars.return_value.all.return_value = [item]
    q.case_code = None                            # 不牽動 PM／承攬案同步

    out = await svc.recompute_totals(390)

    assert out["recomputed"] is True
    assert q.total_price == Decimal("100000.00"), "稅內含 ⇒ 小計即總價，不再 ×1.05"
    assert q.tax_amount == Decimal("0"), "稅內含 ⇒ 稅額不另計"
