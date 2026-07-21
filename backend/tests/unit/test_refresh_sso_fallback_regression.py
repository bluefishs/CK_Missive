# -*- coding: utf-8 -*-
"""
P1 根治 regression（2026-07-21）— refresh 對 SSO 回退重鑄（I7 無痛續命 / L80）

鎖定 `try_mint_session_from_sso_cookie` 守衛順序與回退行為：refresh_token 失效但帶
有效 ck_employee SSO cookie 時，就地重鑄 SSO session（回 TokenResponse），前端既有
「refresh 成功→重試原請求」線路即可透明復原、無整頁 reload、無存檔白填。

前置任一不足（flag off / 無 cookie / JWT 無效 / 無 missive 權限 / user 不存在或停用）
→ 回 None（不 raise），由 refresh 端點維持原 401。

執行方式:
    pytest tests/unit/test_refresh_sso_fallback_regression.py -v

註：refresh 端點與前端重試的完整 e2e（帶真實 ck_employee cookie）由 owner 瀏覽器驗證。
"""
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.api.endpoints.auth import sso_bridge as ssob

MOD = "app.api.endpoints.auth.sso_bridge"


def _req(cookies):
    r = Mock()
    r.cookies = cookies
    r.headers = {}
    return r


@pytest.mark.asyncio
async def test_fallback_none_when_flag_disabled():
    with patch.object(ssob.settings, "CK_SSO_ENABLED", False):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "x"}), Mock())
    assert out is None


@pytest.mark.asyncio
async def test_fallback_none_when_no_sso_cookie():
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"refresh_token": "r"}), Mock())
    assert out is None


@pytest.mark.asyncio
async def test_fallback_none_when_jwt_invalid():
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"), \
         patch.object(ssob, "verify_ck_sso_jwt_auto", return_value=None):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "bad"}), Mock())
    assert out is None


@pytest.mark.asyncio
async def test_fallback_none_when_no_missive_permission():
    emp = Mock(email="a@b.com", systems=["other"])
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"), \
         patch.object(ssob, "verify_ck_sso_jwt_auto", return_value=emp), \
         patch.object(ssob, "has_system_permission", return_value=False):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "ok"}), Mock())
    assert out is None


@pytest.mark.asyncio
async def test_fallback_none_when_user_missing_or_inactive():
    emp = Mock(email="a@b.com", systems=["missive"])
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"), \
         patch.object(ssob, "verify_ck_sso_jwt_auto", return_value=emp), \
         patch.object(ssob, "has_system_permission", return_value=True), \
         patch.object(ssob.AuthService, "get_user_by_email", new=AsyncMock(return_value=None)):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "ok"}), Mock())
    assert out is None

    inactive = Mock(is_active=False)
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"), \
         patch.object(ssob, "verify_ck_sso_jwt_auto", return_value=emp), \
         patch.object(ssob, "has_system_permission", return_value=True), \
         patch.object(ssob.AuthService, "get_user_by_email", new=AsyncMock(return_value=inactive)):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "ok"}), Mock())
    assert out is None


@pytest.mark.asyncio
async def test_fallback_mints_with_sso_ttl_on_happy_path():
    """有效 SSO cookie + missive 權限 + active user → 回 TokenResponse，且用 SSO 8h TTL 重鑄"""
    emp = Mock(email="a@b.com", systems=["missive"])
    user = Mock(is_active=True, email="a@b.com")
    sentinel = Mock(name="TokenResponse")
    gen = AsyncMock(return_value=sentinel)
    with patch.object(ssob.settings, "CK_SSO_ENABLED", True), \
         patch.object(ssob.settings, "CK_SSO_JWT_SECRET", "secret"), \
         patch.object(ssob.settings, "SSO_ACCESS_TOKEN_EXPIRE_MINUTES", 480), \
         patch.object(ssob, "verify_ck_sso_jwt_auto", return_value=emp), \
         patch.object(ssob, "has_system_permission", return_value=True), \
         patch.object(ssob, "get_client_info", return_value=("1.2.3.4", "ua")), \
         patch.object(ssob.AuthService, "get_user_by_email", new=AsyncMock(return_value=user)), \
         patch.object(ssob.AuthService, "generate_login_response", new=gen):
        out = await ssob.try_mint_session_from_sso_cookie(_req({"ck_employee": "ok"}), Mock())
    assert out is sentinel
    # 確認以 SSO 8h TTL 重鑄、且標記 is_refresh
    _, kwargs = gen.call_args
    assert kwargs.get("access_token_ttl_minutes") == 480
    assert kwargs.get("is_refresh") is True
