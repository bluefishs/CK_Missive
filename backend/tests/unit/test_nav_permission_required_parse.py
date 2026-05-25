"""P-57 regression test — sidebar nav permission_required 必須回 list 不能回 JSON 字串

Bug：DB 內 SiteNavigationItem.permission_required 是 TEXT JSON 字串（如 '[]', '["x:y"]'），
若直接回傳前端，frontend filterNavigationItems 用 length === 0 判空誤判
（'[]'.length=2 ≠ 0），導致全部 nav 對無權限用戶可見。

Fix：在 _parse_permission_required helper（同時存於 navigation.py 與 nav_repo）做 JSON parse。

@version 1.0.0
@date 2026-05-07
"""
import pytest

from app.api.endpoints.secure_site_management.navigation import (
    _parse_permission_required as parse_endpoint,
)
from app.repositories.navigation_repository import (
    _parse_permission_required as parse_repo,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        # 空值 → []
        (None, []),
        ("", []),
        ("[]", []),
        # JSON 字串 → list
        ('["documents:read"]', ["documents:read"]),
        ('["a:b","c:d"]', ["a:b", "c:d"]),
        # 已經是 list → 原樣
        (["x:y"], ["x:y"]),
        ([], []),
        # 損壞 JSON → 安全 fallback []
        ("not-json", []),
        ('{"obj":1}', []),  # 非 list 型別
        ("null", []),  # parsed 是 None
        # 預期外型別
        (123, []),
        ({"foo": "bar"}, []),
    ],
)
def test_parse_permission_required_endpoint(raw, expected):
    """endpoint helper 解析 permission_required JSON 字串"""
    assert parse_endpoint(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, []),
        ("[]", []),
        ('["documents:read"]', ["documents:read"]),
        ('["a","b"]', ["a", "b"]),
        (["x"], ["x"]),
        ("invalid", []),
    ],
)
def test_parse_permission_required_repo(raw, expected):
    """repo helper 行為應與 endpoint helper 一致"""
    assert parse_repo(raw) == expected


def test_parse_endpoint_and_repo_alignment():
    """endpoint helper 與 repo helper 必須對相同輸入產出相同結果（否則 root vs children 不一致）"""
    samples = [None, "[]", '["x:y"]', '["a","b"]', "invalid", ["already"], {"obj": 1}]
    for s in samples:
        assert parse_endpoint(s) == parse_repo(s), f"mismatch on {s!r}"
