#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""健康端點的 503 分支要**真的被執行過**，不是只在原始碼裡出現。

## 為什麼有這一支

2026-08-29 由 CK_AaaP 跨 session 點出：他們的 `/api/health` degraded 路徑
是當日新加的，而 8 個提到 health 的測試檔**沒有一個走過它** ——
只有原始碼層的斷言說「`status_code=503` 這個字串在」。

**我這邊一模一樣**：`test_health_verdict_contract.py` 用
`inspect.getsource()` 比對字串，那驗的是「這行程式碼存在」，
不是「這條分支會執行、而且執行結果是對的」。

⇒ 我驗到的是「沒壞時回 200」，而我要驗的是「**壞了會回 503**」。
   **兩件事在測試報告上都是綠的。**

同族（同日、不同層）：
  · 我為「缺權限時顯示說明」寫的 UI，第一次驗證時警示沒出現 ——
    因為**我的身分有那個權限**，條件不成立。我驗到的是
    「不該顯示時沒顯示」，而要驗的是「該顯示時會顯示」。
  · ⇒ 統稱：**我驗的是哪一側？**

## 這一支驗什麼

| 分支 | 注入 | 期望 |
|---|---|---|
| `/api/health` 業務量不足 | 門檻拉到不可能達到 | **503** + `business_data.ok=False` + 說得出原因 |
| `/api/health` 正常 | 不注入 | 200 + `status=healthy` |
| `/api/health/detailed` DB 壞 | `check_database` 回 unhealthy | **503** + `status=unhealthy` + `failing.fatal` **指名** database |
| `/api/health/detailed` AI 全斷 | 所有 provider `available=False` | **200** + `status=degraded` + `failing.degraded` 指名 ai_services |

⚠️ 每一條都驗**兩側**：注入後要壞、不注入要好。
只驗一側的測試會在「分支永遠不執行」時照樣綠。
"""
import os

import pytest

pytestmark = pytest.mark.asyncio


async def test_basic_health_returns_200_when_all_good(client, monkeypatch):
    """基準：業務量達標時是 200。

    ⚠️ 門檻降到 0 是**必要的**：測試庫 ck_documents_test 的
    documents 與 canonical_entities 都是 **0** ⇒ 用正式門檻跑，
    端點會**正確地**回 503。首版沒降門檻，紅的是我的假設而不是端點。
    ⇒ 這裡驗的是**分支邏輯**（達標→200），不是測試庫有多少資料。
    """
    from app.core import health_probe

    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})
    monkeypatch.setenv("HEALTH_MIN_DOCUMENTS", "0")
    monkeypatch.setenv("HEALTH_MIN_KG_ENTITIES", "0")
    monkeypatch.setenv("HEALTH_BUSINESS_CACHE_TTL_S", "0")

    r = await client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "healthy"
    assert body["business_data"]["ok"] is True
    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})


async def test_basic_health_returns_503_when_business_data_below_threshold(
    client, monkeypatch
):
    """**這是重點**：業務量不足時必須真的回 503，不是只有程式碼裡寫著。

    模擬 L43 的情境（volume 掛到空殼 DB）—— 把門檻拉到不可能達到，
    等同於「資料不見了」。
    """
    from app.core import health_probe

    # cache 會讓注入無效 —— 先清掉（這一步漏了會得到一個「碰巧綠」的測試）
    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})
    monkeypatch.setenv("HEALTH_MIN_DOCUMENTS", "999999999")
    monkeypatch.setenv("HEALTH_BUSINESS_CACHE_TTL_S", "0")

    r = await client.get("/api/health")

    assert r.status_code == 503, (
        f"業務量不足卻回 {r.status_code} —— 503 分支沒有被執行。"
        f"body={r.text[:300]}")
    body = r.json()
    assert body["status"] == "unhealthy"
    assert body["business_data"]["ok"] is False
    assert body["business_data"].get("reason"), (
        "回了 503 卻沒說原因 —— 讀的人無法分辨是資料不見了還是查詢壞了")

    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})


async def test_verdict_inputs_is_present_and_honest(client):
    """`verdict_inputs` 要真的下發（跨 repo 契約），且 deciding 兩項都在回應裡。"""
    r = await client.get("/api/health")
    body = r.json()
    vi = body.get("verdict_inputs")
    assert vi, "少了 verdict_inputs —— 那是 CK_AaaP 的探針在讀的欄位"
    assert set(vi) >= {"deciding", "not_covered", "note"}
    for key in vi["deciding"]:
        assert key in body, (
            f"`deciding` 宣告了 `{key}`，而回應裡沒有這個欄位 —— "
            "宣告與實際下發的內容對不上")


@pytest.mark.parametrize("env_key", ["HEALTH_BUSINESS_CHECK_ENABLED"])
async def test_business_check_can_be_disabled_without_lying(client, monkeypatch, env_key):
    """關掉業務量檢查時要**說自己被關掉了**，不能假裝檢查過。

    `{"ok": True, "skipped": True}` —— `skipped` 這個欄位是重點：
    沒有它的話，「檢查通過」與「沒有檢查」在回應上長得一樣。
    """
    from app.core import health_probe

    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})
    monkeypatch.setenv(env_key, "false")

    r = await client.get("/api/health")
    body = r.json()
    assert body["business_data"].get("skipped") is True, (
        "業務量檢查被關掉，而回應沒有說 —— "
        "「檢查通過」與「沒有檢查」不該長得一樣")

    health_probe._business_data_cache.update({"checked_at": 0.0, "result": None})
    os.environ.pop(env_key, None)


@pytest.fixture
async def admin_client():
    """以 **admin** 身分打 API 的 client。

    ⚠️ 專案的 `authenticated_client` 用的是 `mock_current_user`
    （`is_admin=False`）⇒ 打 `/api/health/detailed` 會 403，
    而我首版寫成「403 就 skip」—— **那讓兩條分支永遠沒被執行，
    而報告上顯示 `2 skipped` 看起來像沒事**。
    skip 不是通過；它是「這一條沒有驗」。
    """
    from unittest.mock import MagicMock
    from httpx import AsyncClient, ASGITransport
    from main import app
    from app.api.endpoints.auth import get_current_user
    from app.extended.models import User

    u = MagicMock(spec=User)
    u.id, u.username, u.email = 999, "test_admin", "admin@test"
    u.is_active, u.is_admin, u.is_superuser, u.role = True, True, False, "admin"

    app.dependency_overrides[get_current_user] = lambda: u
    try:
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── /api/health/detailed ─────────────────────────────────────────────
#
# ⚠️ 這兩條原本只寫在本檔的表格裡而沒有實作 —— **宣稱比做到的多**，
# 正是本檔要治的病的另一種形態。補齊。
#
# 這支端點需要 admin，所以用 `authenticated_client` 並讓 mock user 是 admin。

async def test_detailed_returns_503_and_names_the_fatal_check(
    admin_client, monkeypatch
):
    """DB 檢查壞掉時：503 + status=unhealthy + **指名**是 database 壞了。

    「指名」是重點：只說 unhealthy 而不說哪一項，讀的人還是得自己翻六個子檢查。
    """
    from app.services.system import health_service as hs

    async def _bad_db(self):
        return {"status": "unhealthy", "message": "injected"}

    monkeypatch.setattr(hs.SystemHealthService, "check_database", _bad_db, raising=True)

    r = await admin_client.get("/api/health/detailed")
    assert r.status_code != 403, (
        "admin 身分仍被擋 —— fixture 沒生效，這一條等於沒驗")

    assert r.status_code == 503, (
        f"DB 檢查回 unhealthy 卻得到 {r.status_code} —— fatal 分支沒有被執行。"
        f"body={r.text[:300]}")
    body = r.json()
    assert body["status"] == "unhealthy"
    assert "database" in body.get("failing", {}).get("fatal", []), (
        f"回了 503 但沒指名是哪一項壞了：failing={body.get('failing')}")


async def test_detailed_degraded_does_not_return_503(admin_client, monkeypatch):
    """AI 全斷時：**200 + degraded**，不是 503。

    AI 掛掉不該讓公文系統被判死 —— 但也不該說「All systems operational」。
    """
    from app.core import ai_connector

    class _AllDown:
        async def check_health(self):
            return {
                "groq": {"available": False, "message": "injected"},
                "ollama": {"available": False, "message": "injected"},
            }

    monkeypatch.setattr(ai_connector, "get_ai_connector", lambda: _AllDown(), raising=True)

    r = await admin_client.get("/api/health/detailed")
    assert r.status_code != 403, "admin 身分仍被擋 —— fixture 沒生效"

    assert r.status_code == 200, (
        f"AI 全斷卻回 {r.status_code} —— degraded 不該是 503，"
        "那會讓推論服務掛掉時整站被判死")
    body = r.json()
    assert body["status"] == "degraded", f"status={body.get('status')}"
    assert "ai_services" in body.get("failing", {}).get("degraded", []), (
        f"degraded 沒指名 ai_services：failing={body.get('failing')}")
    assert "All systems operational" not in (body.get("message") or ""), (
        "AI 全斷而訊息仍說「所有系統正常」—— 那正是本日修掉的那句話")
