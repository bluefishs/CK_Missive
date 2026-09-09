# -*- coding: utf-8 -*-
"""發票已開 ⇒ 該筆請款已成立（2026-09-09 owner：/erp/quotations/793「發票 78,960｜請款 0」）。

一份實作 `billing_service.settle_placeholder_for_invoice`，發票建立（invoice_service）與總表匯入
（quotation_legacy_import）都走它。這裡鎖：①語意（指定 billing／唯一同額佔位／多筆不猜／有日期不動）
②兩個呼叫端都有接。
"""
import inspect
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.erp.billing_service import settle_placeholder_for_invoice


def _db(rows_by_call):
    """依序回傳每次 execute 的結果物件（first()/all()/scalar()），並記錄 SQL。"""
    db = MagicMock()
    calls = []

    async def _execute(stmt, params=None):
        calls.append((str(stmt), params))
        res = MagicMock()
        data = rows_by_call.pop(0) if rows_by_call else []
        res.first.return_value = data[0] if data else None
        res.all.return_value = data
        res.scalar.return_value = data[0][0] if data else None
        return res

    db.execute = AsyncMock(side_effect=_execute)
    db._calls = calls
    return db


@pytest.mark.asyncio
async def test_no_invoice_date_does_nothing():
    db = _db([])
    assert await settle_placeholder_for_invoice(db, quotation_id=1, invoice_date=None, amount=100) is None
    assert db.execute.await_count == 0


@pytest.mark.asyncio
async def test_bound_billing_without_date_gets_invoice_date():
    db = _db([[(460,)], []])  # SELECT 找到無日期的 460；UPDATE
    out = await settle_placeholder_for_invoice(db, quotation_id=793, invoice_date=date(2026, 7, 30), amount=78960, billing_id=460)
    assert out == 460
    sql, params = db._calls[-1]
    assert "UPDATE erp_billings SET billing_date" in sql and params["b"] == 460 and params["d"] == date(2026, 7, 30)


@pytest.mark.asyncio
async def test_unique_same_amount_placeholder_is_settled():
    db = _db([[(461,)], []])
    out = await settle_placeholder_for_invoice(db, quotation_id=794, invoice_date=date(2026, 7, 30), amount=Decimal("19950"))
    assert out == 461
    assert "billing_date IS NULL" in db._calls[0][0] and "NOT EXISTS" in db._calls[0][0]


@pytest.mark.asyncio
async def test_two_candidates_do_not_guess():
    db = _db([[(1,), (2,)]])
    assert await settle_placeholder_for_invoice(db, quotation_id=1, invoice_date=date(2026, 1, 1), amount=100) is None
    assert db.execute.await_count == 1  # 沒有 UPDATE


@pytest.mark.asyncio
async def test_bound_billing_already_dated_is_left_alone():
    db = _db([[]])  # 指定的 billing 已有日期 ⇒ SELECT 查不到
    assert await settle_placeholder_for_invoice(db, quotation_id=1, invoice_date=date(2026, 1, 1), amount=100, billing_id=5) is None
    assert db.execute.await_count == 1


def test_both_entry_points_call_the_one_implementation():
    from app.services.erp import invoice_service, quotation_legacy_import
    assert "settle_placeholder_for_invoice(" in inspect.getsource(invoice_service)
    src = inspect.getsource(quotation_legacy_import)
    assert src.count("_settle_invoice_billing(") >= 3  # 定義 + 更新分支 + 新建分支
    assert "settle_placeholder_for_invoice(" in src
