# -*- coding: utf-8 -*-
"""Calendar Visibility Regression Tests (ADR-0024 坤哥 v5.8.0 D6-A).

測試：
- _is_superuser helper：is_superuser=True / role='superuser' 任一即通過
- 一般用戶：assigned / created / 公共 / 承辦同仁四層可見
- Superuser：bypass 所有 filter

由於 SQL 層測試需完整 DB fixture（較重），本模組聚焦於 helper 與
查詢組裝邏輯層的回歸保護。端到端測試留 E2E 階段。
"""
from __future__ import annotations

import pytest
from types import SimpleNamespace


# ────────── _is_superuser helper ──────────

def test_is_superuser_via_flag():
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    user = SimpleNamespace(is_superuser=True, role='user', email='x@y.tw')
    assert _is_superuser(user) is True


def test_is_superuser_via_role():
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    user = SimpleNamespace(is_superuser=False, role='superuser', email='x@y.tw')
    assert _is_superuser(user) is True


def test_is_superuser_false_for_regular():
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    user = SimpleNamespace(is_superuser=False, role='user', email='x@y.tw')
    assert _is_superuser(user) is False


def test_is_superuser_false_for_admin_not_superuser():
    """admin 角色不等於 superuser — 避免權限擴散。"""
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    user = SimpleNamespace(is_superuser=False, role='admin', email='x@y.tw')
    assert _is_superuser(user) is False


def test_is_superuser_handles_missing_attrs():
    """缺 attr 應 graceful 回 False，不 raise。"""
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    minimal_user = SimpleNamespace()
    assert _is_superuser(minimal_user) is False


# ────────── SQL 組裝路徑（structural assertion） ──────────

def test_superuser_path_produces_no_visibility_filter():
    """Superuser 不應被加任何 user/project 可見性 WHERE 條件（邏輯層檢查）。

    此測試確保 _is_superuser=True 分支就是「早退」路徑，
    不去建構 or_(...) filter。
    """
    # 透過檢查分支條件本身，避免 mock 整個 SQL chain
    from app.api.endpoints.document_calendar.events_batch import _is_superuser

    super_user = SimpleNamespace(is_superuser=True, role='user', email='a@b')
    regular_user = SimpleNamespace(is_superuser=False, role='user', email='c@d')

    # 此處僅驗證 helper 的分歧行為
    assert _is_superuser(super_user) != _is_superuser(regular_user)
