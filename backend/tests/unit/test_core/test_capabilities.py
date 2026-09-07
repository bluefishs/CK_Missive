# -*- coding: utf-8 -*-
"""頁面能力宣告的唯一來源（2026-09-07 收斂 B）。

鎖三件事：①頁面沒有宣告 ⇒ 只要求登入（不自己發明限制）
②有宣告 ⇒ 沒有該碼就 403 ③多頁取聯集（一支 API 被兩頁共用）。
`_cache` 直接塞值，不打 DB —— 測的是判準，不是載入。
"""
from types import SimpleNamespace
import json, time
import pytest

from app.core import capabilities as cap


def _u(perms, role="staff"):
    return SimpleNamespace(role=role, is_admin=False, is_superuser=False, permissions=json.dumps(perms))


@pytest.fixture(autouse=True)
def _prime_cache():
    cap._cache = {"/erp/ledger": ["reports:ledger:view"], "/ai/erp-graph": ["reports:erp_graph:view"], "/open": []}
    cap._loaded_at = time.monotonic()
    yield
    cap._cache, cap._loaded_at = {}, 0.0


async def _run(dep, user):
    return await dep(current_user=user)


@pytest.mark.asyncio
async def test_undeclared_page_requires_login_only():
    dep = cap.require_page_permission("/open")
    assert await _run(dep, _u([])) is not None
    dep2 = cap.require_page_permission("/no-such-page")
    assert await _run(dep2, _u([])) is not None


@pytest.mark.asyncio
async def test_declared_page_blocks_without_code():
    from app.core.exceptions import ForbiddenException
    dep = cap.require_page_permission("/erp/ledger")
    with pytest.raises(ForbiddenException):
        await _run(dep, _u(["reports:finance:view"]))
    assert await _run(dep, _u(["reports:ledger:view"])) is not None


@pytest.mark.asyncio
async def test_multi_page_is_union():
    dep = cap.require_page_permission("/erp/ledger", "/ai/erp-graph")
    assert await _run(dep, _u(["reports:erp_graph:view"])) is not None
    assert await _run(dep, _u(["reports:ledger:view"])) is not None


@pytest.mark.asyncio
async def test_superuser_short_circuits():
    dep = cap.require_page_permission("/erp/ledger")
    assert await _run(dep, _u([], role="superuser")) is not None


def test_referenced_pages_are_tracked():
    cap.require_page_permission("/erp/quotations")
    assert "/erp/quotations" in cap._referenced_pages
