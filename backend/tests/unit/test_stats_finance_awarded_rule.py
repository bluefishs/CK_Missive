# -*- coding: utf-8 -*-
"""承攬金額規則只有一份（L149 收斂存量三處後的回歸鎖，2026-09-09）。

三件事：
1. `pick_awarded` 的順序＝議價 → 契約 → 報價總價，取第一個非零（0 與 None 都算沒有）。
2. SQL 片段 `awarded_amount_case_only` 與 `winning_amount_expr` 的形狀固定——
   消費端靠它們組查詢，改了形狀就是改了每一支統計。
3. 成案端點（A131）必須經過 `assert_case_scope`——此前任何登入者都能把任何案成案。
   用 inspect 鎖是本 repo 的既有做法（`test_promote_requires_amount.py`）；
   行為層的範圍判準本身另有 `core/case_scope` 的測試。
"""
from decimal import Decimal
import inspect

import pytest

from app.services.stats.finance import (
    awarded_amount_case_only,
    pick_awarded,
    winning_amount_expr,
)


@pytest.mark.parametrize(
    "winning, contract, quote, expected",
    [
        (Decimal("100"), Decimal("200"), Decimal("300"), Decimal("100")),
        (None, Decimal("200"), Decimal("300"), Decimal("200")),
        (0, Decimal("200"), Decimal("300"), Decimal("200")),           # 議價未填是 0 不是 NULL
        (None, None, Decimal("300"), Decimal("300")),
        (None, 0, "300.00", "300.00"),                                   # 字串金額也吃得下
        (None, None, None, None),
        (0, 0, 0, None),
    ],
)
def test_pick_awarded_order(winning, contract, quote, expected):
    assert pick_awarded(winning, contract, quote) == expected


def test_sql_fragments_shape():
    assert winning_amount_expr("c") == "NULLIF(c.winning_amount, 0)"
    assert awarded_amount_case_only("cp") == "COALESCE(NULLIF(cp.winning_amount, 0), cp.contract_amount)"


def test_promote_endpoint_checks_case_scope():
    from app.api.endpoints.pm import cases as pm_cases

    src = inspect.getsource(pm_cases.promote_to_project)
    assert "assert_case_scope" in src, "成案端點少了身分範圍檢查（A131）"
    assert "require_auth()" in src
