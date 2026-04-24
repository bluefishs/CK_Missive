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
    src = inspect.getsource(subscriptions.list_bookmarks)
    assert "TenderBookmark.user_id == current_user.id" in src, (
        "list_bookmarks must filter by user_id"
    )
