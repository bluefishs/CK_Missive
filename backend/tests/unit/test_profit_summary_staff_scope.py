# -*- coding: utf-8 -*-
"""統計卡的分母不得比列表寬：承辦交集只有一份（2026-09-09）。

owner 回報：/erp/quotations 選承辦「邱元宏」＋02 承攬報價，列表 85 張，
卡片「承攬金額」卻是全公司 112 張的 21,493,663；/erp/client-accounts 同條件是 5,057,835。
真因＝`list_quotations` 有交集承辦案號、`get_profit_summary` 沒有 ⇒ 卡片不知道使用者選了誰。

鎖三件事：
1. `narrow_scope_to_staff` 的語意（None 不動／交集／空集合回 {"__none__"}）。
2. 列表與摘要**都**走這一份（inspect：兩個方法都呼叫它，且檔案裡不再有第二份交集寫法）。
3. 端點把 `staff_user_id` 轉給 service（inspect）。
"""
import inspect
from unittest.mock import AsyncMock, patch

import pytest

from app.services.erp import quotation_service as qs


@pytest.mark.asyncio
async def test_narrow_none_staff_keeps_scope():
    assert await qs.narrow_scope_to_staff(None, None, None) is None
    assert await qs.narrow_scope_to_staff(None, {"A", "B"}, None) == {"A", "B"}


@pytest.mark.asyncio
async def test_narrow_intersects_with_scope():
    with patch("app.repositories.erp.case_staff.case_codes_of_user", new=AsyncMock(return_value={"A", "C"})):
        assert await qs.narrow_scope_to_staff(None, {"A", "B"}, 6) == {"A"}
        # 全公司視角（scope=None）⇒ 直接用承辦案號
        assert await qs.narrow_scope_to_staff(None, None, 6) == {"A", "C"}


@pytest.mark.asyncio
async def test_narrow_empty_intersection_is_sentinel_not_all():
    with patch("app.repositories.erp.case_staff.case_codes_of_user", new=AsyncMock(return_value={"Z"})):
        assert await qs.narrow_scope_to_staff(None, {"A"}, 6) == {"__none__"}
    with patch("app.repositories.erp.case_staff.case_codes_of_user", new=AsyncMock(return_value=set())):
        assert await qs.narrow_scope_to_staff(None, None, 6) == {"__none__"}


def test_list_and_summary_share_one_helper():
    src_list = inspect.getsource(qs.ERPQuotationService.list_quotations)
    src_sum = inspect.getsource(qs.ERPQuotationService.get_profit_summary)
    assert "narrow_scope_to_staff(" in src_list
    assert "narrow_scope_to_staff(" in src_sum
    # 檔案裡不得再有第二份「承辦交集」寫法
    whole = inspect.getsource(qs)
    assert whole.count("case_codes_of_user(") == 1, "承辦案號交集只能寫在 narrow_scope_to_staff 裡"


def test_endpoint_forwards_staff_user_id():
    from app.api.endpoints.erp import quotations as ep
    src = inspect.getsource(ep.get_profit_summary)
    assert "staff_user_id=req.staff_user_id" in src
