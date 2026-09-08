# -*- coding: utf-8 -*-
"""可見範圍與「承辦同仁」篩選的交集 —— 2026-09-08 的 500 回歸鎖。

## 事故

owner（業務同仁王駿穠）打開 `/erp/quotations` 並挑了承辦同仁，
`/api/erp/quotations/list` 連續 **500**：

    TypeError: 'CompoundSelect' object is not iterable

根因是**同一個值有兩種用法，而只有其中一種撐得住**：
`_quotation_scope` 回的是 `RLSFilter.get_user_accessible_case_codes()` ——
一個**還沒執行的 SQL 述句**。丟進 `case_code.in_(...)` 完全正常
（SQLAlchemy 接受子查詢），所以這條路徑上線後一直沒事；
但服務層在「使用者也挑了承辦同仁」時要做 `set(範圍) & mine` ⇒
對述句 `set()` 就炸了。

⇒ **症狀只在特定組合出現（非管理員＋有選承辦），而那正好是使用者的日常。**
   管理員測不出來，因為管理員的範圍是 `None`。

修法兩層：①`_quotation_scope` 改回集合（唯一定義走 `case_scope`）
②服務層入口對述句就地執行成集合（防呆），且解不開時**限縮成空**不是放行全部。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.erp.quotation_service import ERPQuotationService


def _params(**kw):
    p = MagicMock()
    p.year = None; p.status = None; p.case_code = None; p.search = None
    p.skip = 0; p.limit = 20; p.sort_by = "id"; p.sort_order = None
    p.include_unawarded = True; p.category = None; p.case_status = None
    p.client_name = None; p.card = None; p.anomaly = None
    p.staff_user_id = None
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _service():
    db = MagicMock()
    db.execute = AsyncMock()
    svc = ERPQuotationService(db)
    # 只驗「交集算不算得出來」——查詢本身回空，讓測試停在該停的地方
    svc.repo = MagicMock()
    svc.repo.filter_quotations = AsyncMock(return_value=([], 0))
    return svc, db


@pytest.mark.asyncio
async def test_set_scope_intersects_with_staff_filter(monkeypatch):
    """集合形式：交集要算對，且結果只能**變小**不能變大。"""
    svc, _db = _service()
    monkeypatch.setattr(
        "app.repositories.erp.case_staff.case_codes_of_user",
        AsyncMock(return_value={"A", "B"}),
    )
    await svc.list_quotations(_params(staff_user_id=7),
                              accessible_case_codes={"B", "C"})
    passed = svc.repo.filter_quotations.call_args.kwargs["accessible_case_codes"]
    assert passed == {"B"}, "使用者自選的承辦只能在可見範圍之內再縮小"


@pytest.mark.asyncio
async def test_statement_scope_does_not_explode(monkeypatch):
    """述句形式：**不得 500**（這就是 09-08 那個 TypeError）。"""
    svc, db = _service()
    monkeypatch.setattr(
        "app.repositories.erp.case_staff.case_codes_of_user",
        AsyncMock(return_value={"A", "B"}),
    )
    # 一個不可迭代、但可被 db.execute 執行的東西 —— 就是 CompoundSelect 的形狀
    stmt = MagicMock()
    del stmt.__iter__          # 確保 set() 會失敗（MagicMock 預設可迭代性不可靠）
    db.execute.return_value = MagicMock(all=MagicMock(return_value=[("A",), ("Z",)]))

    await svc.list_quotations(_params(staff_user_id=7), accessible_case_codes=stmt)

    passed = svc.repo.filter_quotations.call_args.kwargs["accessible_case_codes"]
    assert passed == {"A"}, "述句要就地執行成集合（{A,Z}），再與承辦（{A,B}）取交集"


@pytest.mark.asyncio
async def test_unresolvable_scope_fails_closed(monkeypatch):
    """範圍解不開時要**限縮成空**，不是放行全部。

    守衛失效的安全方向是「看不到」——若退成 None（不限縮），
    一次解析失敗就等於把全公司的案子攤開給所有人，而畫面上完全看不出來。
    """
    svc, db = _service()
    monkeypatch.setattr(
        "app.repositories.erp.case_staff.case_codes_of_user",
        AsyncMock(return_value={"A"}),
    )
    stmt = MagicMock()
    del stmt.__iter__
    db.execute.side_effect = RuntimeError("boom")

    await svc.list_quotations(_params(staff_user_id=7), accessible_case_codes=stmt)

    passed = svc.repo.filter_quotations.call_args.kwargs["accessible_case_codes"]
    assert passed == {"__none__"}, "空範圍 ∩ 任何東西＝空 ⇒ 查不到，而不是全都看得到"
