# -*- coding: utf-8 -*-
"""填報當下的檢核與自動關聯（2026-09-07 owner：「應在填報時就有完善檢核與自動關聯機制」）。

這一組測試鎖的是「**事後才發現**」那一族的入口版本：

| 事後發現（週稽核） | 填報當下（本組） |
|---|---|
| weekly 107 名稱對得到主檔卻沒填鍵 | 應付建立時解析不到就 raise，不靜靜留一個沒有鍵的名字 |
| 09-06 應付 #51「兩家併寫」拆不了（沒有憑證） | 建立時就擋下併寫，請人一家一筆 |
| weekly 104 ② 發票額 > 請款額 | 建立時擋 |
| weekly 104 ⑤ 發票稅額非 5% | 建立時擋 |
| weekly 99 應付／發票沒有 billing_id | 建立時自動綁（同額且唯一才綁，兩期同額不猜） |
| 09-06 收款額 > 請款額（會讓應收未收變負） | 更新時擋 |

**負向控制同樣重要**：正常的填報不得被擋（免稅發票 tax=0、金額相等、名稱精確命中）。
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.erp.party_resolver import PartyResolver, normalize_name, split_candidates


# ── 名稱解析器（純函式部分，不打 DB）────────────────────────────────
class TestNameNormalization:
    def test_normalize_strips_org_suffix_and_spaces(self):
        assert normalize_name("張啟良建築師事務所") == normalize_name("張啟良建築師")
        assert normalize_name("顏新元 代書") == "顏新元代書"
        assert normalize_name("竣吉不動產估價師事務所") == "竣吉不動產估價師"

    def test_split_detects_two_orgs_in_one_cell(self):
        # 09-06 應付 #51 的真實資料
        assert split_candidates("銢欣有限公司乃耳企業社") == ["銢欣有限公司", "乃耳企業社"]

    def test_split_detects_joiner(self):
        # 同一批匯入的另一種寫法
        assert split_candidates("楊長燁加李雅倫") == ["楊長燁", "李雅倫"]

    def test_single_vendor_is_not_split(self):
        assert split_candidates("政崴資訊顧問有限公司") == []
        assert split_candidates("祐鴻測繪科技有限公司") == []


def _vendor(vid: int, name: str, tax_id: str | None = None):
    return SimpleNamespace(id=vid, vendor_name=name, tax_id=tax_id, vendor_code=None)


def _resolver_with(rows):
    db = MagicMock()
    r = PartyResolver(db)
    r._all = AsyncMock(return_value=rows)  # type: ignore[method-assign]
    return r


class TestPartyResolver:
    @pytest.mark.asyncio
    async def test_exact_match(self):
        r = _resolver_with([_vendor(1, "祐鴻測繪科技有限公司")])
        res = await r.resolve("祐鴻測繪科技有限公司")
        assert res.vendor_id == 1 and res.matched_by == "exact"

    @pytest.mark.asyncio
    async def test_abbreviation_matches_master(self):
        r = _resolver_with([_vendor(59, "張啟良建築師事務所")])
        res = await r.resolve("張啟良建築師")
        assert res.vendor_id == 59 and res.matched_by in ("normalized", "prefix")

    @pytest.mark.asyncio
    async def test_tax_id_wins_over_name(self):
        r = _resolver_with([_vendor(76, "銢欣有限公司", "80321095"), _vendor(86, "司乃耳企業社", "82349892")])
        res = await r.resolve("名字打錯了", tax_id="82349892")
        assert res.vendor_id == 86 and res.matched_by == "tax_id"

    @pytest.mark.asyncio
    async def test_two_vendors_in_one_name_is_refused_not_guessed(self):
        r = _resolver_with([_vendor(76, "銢欣有限公司"), _vendor(86, "乃耳企業社")])
        res = await r.resolve("銢欣有限公司乃耳企業社")
        assert res.vendor_id is None, "併寫不得自動選一家 —— 錢會記到錯的廠商"
        assert res.split_into == ["銢欣有限公司", "乃耳企業社"]
        assert "併寫" in res.reason

    @pytest.mark.asyncio
    async def test_unknown_name_says_so(self):
        r = _resolver_with([_vendor(71, "林宥廷測量技師事務所")])
        res = await r.resolve("林晉廷")
        assert res.vendor_id is None and "主檔沒有" in res.reason

    @pytest.mark.asyncio
    async def test_ambiguous_returns_candidates_not_a_guess(self):
        r = _resolver_with([_vendor(57, "顏新元地政士事務所"), _vendor(109, "顏新元地政士")])
        res = await r.resolve("顏新元")
        assert res.vendor_id is None and len(res.candidates) == 2


# ── 發票：填報當下的檢核與自動綁請款 ──────────────────────────────
class _Svc:
    """只取 ERPInvoiceService 的 _validate_and_link 來測（不建構整個服務）。"""

    def __init__(self, db):
        self.db = db

    from app.services.erp.invoice_service import ERPInvoiceService as _S
    _validate_and_link = _S._validate_and_link


def _db_with(billings, taken_billing_ids=()):
    """execute 依序回：billings（scalars().all()）、已被綁的 billing_id、單筆 billing。"""
    db = MagicMock()

    def _result_for(stmt):
        text = str(stmt)
        res = MagicMock()
        if "erp_invoices" in text or "erp_invoice" in text.lower():
            res.scalars.return_value.all.return_value = list(taken_billing_ids)
        elif " WHERE erp_billings.id = " in text or "erp_billings.id =" in text:
            res.scalars.return_value.first.return_value = next(iter(billings), None)
        else:
            res.scalars.return_value.all.return_value = list(billings)
            res.scalars.return_value.first.return_value = next(iter(billings), None)
        return res

    db.execute = AsyncMock(side_effect=lambda stmt, *a, **k: _result_for(stmt))
    return db


def _billing(bid, amount, period="第一期"):
    return SimpleNamespace(id=bid, billing_amount=Decimal(str(amount)),
                           billing_period=period, erp_quotation_id=1)


class TestInvoiceEntryGuards:
    @pytest.mark.asyncio
    async def test_tax_must_be_five_percent_or_zero(self):
        svc = _Svc(_db_with([]))
        data = SimpleNamespace(amount=Decimal("10500"), tax_amount=Decimal("500"),
                               billing_id=None, erp_quotation_id=None)
        # 10,500 含稅的稅額是 500 —— 應通過
        await svc._validate_and_link(data)

        bad = SimpleNamespace(amount=Decimal("10500"), tax_amount=Decimal("2000"),
                              billing_id=None, erp_quotation_id=None)
        with pytest.raises(ValueError, match="不相稱"):
            await svc._validate_and_link(bad)

    @pytest.mark.asyncio
    async def test_zero_tax_is_allowed(self):
        """免稅／未開稅：09-06 的 CK2025_PM_02_108 就是 tax=0，不得被擋。"""
        svc = _Svc(_db_with([]))
        data = SimpleNamespace(amount=Decimal("49000"), tax_amount=Decimal("0"),
                               billing_id=None, erp_quotation_id=None)
        await svc._validate_and_link(data)

    @pytest.mark.asyncio
    async def test_amount_over_billing_is_refused(self):
        b = _billing(18, "434000")
        svc = _Svc(_db_with([b]))
        data = SimpleNamespace(amount=Decimal("455700"), tax_amount=Decimal("0"),
                               billing_id=18, erp_quotation_id=1)
        with pytest.raises(ValueError, match="超過所屬請款"):
            await svc._validate_and_link(data)

    @pytest.mark.asyncio
    async def test_auto_links_unique_same_amount_billing(self):
        b = _billing(18, "434000")
        svc = _Svc(_db_with([b]))
        data = SimpleNamespace(amount=Decimal("434000"), tax_amount=Decimal("0"),
                               billing_id=None, erp_quotation_id=1)
        await svc._validate_and_link(data)
        assert data.billing_id == 18, "同額且唯一未綁 ⇒ 自動綁"

    @pytest.mark.asyncio
    async def test_two_same_amount_billings_are_not_guessed(self):
        bs = [_billing(18, "100000", "第一期"), _billing(19, "100000", "第二期")]
        svc = _Svc(_db_with(bs))
        data = SimpleNamespace(amount=Decimal("100000"), tax_amount=Decimal("0"),
                               billing_id=None, erp_quotation_id=1)
        await svc._validate_and_link(data)
        assert data.billing_id is None, "兩期同額就不猜 —— 猜錯會把錢算到別期而報表看不出來"
