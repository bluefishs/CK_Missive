# -*- coding: utf-8 -*-
"""SSO 憑證真的死掉時，必須明講「請重新登入」（2026-08-07 回歸鎖）。

owner 實測：08:49 SSO 登入 → ck_employee 8h → 16:49 到期；16:39 的 refresh 仍成功
並發出一張到 17:39 的 session；17:39 到期後 refresh 已無憑證可重鑄 → 401。

前端有一道守衛（L74/I-series）：相信自己已登入時，單次 401 + refresh 失敗不清
session、不跳登入頁，只讓該請求失敗。對**暫時性** 401 那是對的，但它分辨不出永久
失效 —— 結果 owner 的刪除動作直接消失（紀錄 391 仍在），且會一直點一直失敗到手動
重整為止。

修法遵循 L74 原則「明確事件優先於被動檢查」：由伺服器宣告 `X-Reauth-Required`，
前端才有依據推翻自己的樂觀假設。

**收窄條件比訊號本身更重要**：完全沒帶 refresh_token 的請求（匿名首載、bootstrap
進行中）不得帶這個 header —— 那正是「閃回登入頁」反覆回歸的觸發路徑。

本測試直接呼叫**真的** endpoint 函式（`refresh_token`），不重寫它的判斷邏輯 ——
否則測試會變成同義反覆：把 session.py 改回去它照樣過。
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


class _FakeRequest:
    """只提供 endpoint 會碰到的 cookies；slowapi 的 limiter 也會讀 request。"""

    def __init__(self, cookies=None):
        self.cookies = cookies or {}
        self.headers = {}
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.state = type("S", (), {})()
        self.scope = {"type": "http"}
        self.url = type("U", (), {"path": "/api/auth/refresh"})()
        self.method = "POST"


async def _run(monkeypatch, *, cookies, sso_mint):
    """跑真的 endpoint，把外部相依（DB 驗證、SSO 重鑄）換掉。"""
    from app.api.endpoints.auth import session as mod

    async def _fake_verify(_db, _tok):
        return None  # refresh_token 一律視為失效 → 逼進 SSO 重鑄分支

    async def _fake_mint(_req, _db):
        return sso_mint

    monkeypatch.setattr(mod.AuthService, "verify_refresh_token", _fake_verify)
    monkeypatch.setattr(mod, "try_mint_session_from_sso_cookie", _fake_mint)

    # 繞過 slowapi 裝飾器（單元測試不驗速率限制）
    fn = getattr(mod.refresh_token, "__wrapped__", mod.refresh_token)
    return await fn(request=_FakeRequest(cookies), refresh_request=None, db=None)


@pytest.mark.asyncio
async def test_dead_credential_declares_reauth_required(monkeypatch):
    """曾經有憑證、現在確定死了 → 必須明講要重新登入。"""
    with pytest.raises(HTTPException) as ei:
        await _run(monkeypatch, cookies={"refresh_token": "expired"}, sso_mint=None)
    assert ei.value.status_code == 401
    assert (ei.value.headers or {}).get("X-Reauth-Required") == "1", (
        "SSO 憑證已死時沒有宣告必須重登，前端守衛會把它當暫時性 401，"
        f"使用者將一直靜默失敗到手動重整。實際 headers={ei.value.headers}"
    )


@pytest.mark.asyncio
async def test_anonymous_bootstrap_does_not_declare_reauth(monkeypatch):
    """完全沒帶 refresh_token（匿名首載/bootstrap）→ 不得宣告，否則會閃回登入頁。"""
    with pytest.raises(HTTPException) as ei:
        await _run(monkeypatch, cookies={}, sso_mint=None)
    assert ei.value.status_code == 401
    assert "X-Reauth-Required" not in (ei.value.headers or {}), (
        "匿名/bootstrap 的 401 被宣告成必須重登 —— 這正是「閃回登入頁」反覆回歸的觸發路徑"
    )


@pytest.mark.asyncio
async def test_successful_sso_remint_does_not_raise(monkeypatch):
    """正向：SSO 還能重鑄時不得 401，否則上面兩支只是「永遠會拋」而無鑑別力。"""
    from app.api.endpoints.auth import session as mod

    # 不用真的 TokenResponse —— 本測試要問的是「有沒有拋 401」，
    # 綁 schema 欄位只會讓它在無關的 schema 演進時變紅。
    class _Minted:
        def model_dump(self, **_kw):
            return {"access_token": "a"}

    monkeypatch.setattr(mod.AuthService, "set_auth_cookies", lambda *a, **k: None)
    resp = await _run(monkeypatch, cookies={"refresh_token": "expired"}, sso_mint=_Minted())
    assert resp is not None and resp.status_code == 200
