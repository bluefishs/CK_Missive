"""Regression test (2026-04-24):
Tender bookmark endpoints must scope per current_user.

Protects against the regression where `list_bookmarks` returned every
bookmark in the DB (global) and `create_bookmark` stored user_id=NULL
— letting one user see all other users' tender bookmarks.
"""
import inspect

from app.api.endpoints.tender_module import subscriptions


def _params(func):
    return inspect.signature(func).parameters


def test_list_bookmarks_requires_current_user():
    p = _params(subscriptions.list_bookmarks)
    assert "current_user" in p, (
        "list_bookmarks must take a current_user dependency for per-user scoping"
    )


def test_create_bookmark_requires_current_user():
    p = _params(subscriptions.create_bookmark)
    assert "current_user" in p, (
        "create_bookmark must take current_user to set user_id"
    )


def test_update_bookmark_requires_current_user():
    p = _params(subscriptions.update_bookmark)
    assert "current_user" in p


def test_delete_bookmark_requires_current_user():
    p = _params(subscriptions.delete_bookmark)
    assert "current_user" in p


def test_create_bookmark_source_uses_user_id():
    """Source-level check: create_bookmark body must pass user_id
    to the TenderBookmark constructor."""
    src = inspect.getsource(subscriptions.create_bookmark)
    assert "user_id=current_user.id" in src, (
        "create_bookmark must bind user_id=current_user.id"
    )


def test_list_bookmark_source_filters_user_id():
    """v6.9 R4-2 (ADR-0025) 後升級：list_bookmarks 改用 expand_user_alias 展開 alias group。

    舊測試期望 `TenderBookmark.user_id == current_user.id` 單一身份過濾，但 alias 多帳號
    用戶會看不到自己其他 alias 的書籤。修法後改用 `TenderBookmark.user_id.in_(alias_ids)`。

    新斷言：仍然按 user_id 過濾（防全域裸露），但接受 alias-aware 展開模式。
    """
    src = inspect.getsource(subscriptions.list_bookmarks)
    # 要不就是 legacy single-user 過濾，要不就是 alias-aware 多 ID 過濾 — 任一即可
    legacy_pattern = "TenderBookmark.user_id == current_user.id" in src
    alias_pattern = "TenderBookmark.user_id.in_(alias_ids)" in src and "expand_user_alias" in src
    assert legacy_pattern or alias_pattern, (
        "list_bookmarks must filter by user_id (legacy single == OR alias-aware .in_())"
    )
