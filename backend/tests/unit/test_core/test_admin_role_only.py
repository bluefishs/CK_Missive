# -*- coding: utf-8 -*-
"""管理員判定只看角色（2026-09-07 權限收斂 A）。

此前是「旗標 OR 角色」，`is_admin` 因此成為凌駕權限清單的第三份宣告：
角色與權限清單都是財務、旗標卻讓她仍能進使用者管理，而權限管理頁上看不出來。
這一組鎖住：**旗標不再是獨立來源**。負向控制同樣重要 —— 角色是 admin 的人不得被誤擋。
"""
from types import SimpleNamespace

from app.core.dependencies import is_admin_user, is_superuser_user


def _u(role, is_admin=False, is_superuser=False):
    return SimpleNamespace(role=role, is_admin=is_admin, is_superuser=is_superuser)


def test_flag_alone_does_not_grant_admin():
    assert is_admin_user(_u("staff", is_admin=True)) is False
    assert is_admin_user(_u("finance", is_admin=True)) is False


def test_role_alone_grants_admin():
    assert is_admin_user(_u("admin")) is True
    assert is_admin_user(_u("superuser")) is True


def test_superuser_is_role_only():
    assert is_superuser_user(_u("superuser")) is True
    assert is_superuser_user(_u("admin", is_superuser=True)) is False


def test_none_is_not_admin():
    assert is_admin_user(None) is False and is_superuser_user(None) is False
