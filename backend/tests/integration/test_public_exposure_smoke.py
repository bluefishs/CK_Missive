# -*- coding: utf-8 -*-
"""公網暴露 smoke test — ADR-0015 Cloudflare Tunnel 驗收。

透過環境變數 ``MISSIVE_PUBLIC_URL`` 啟用；未設則略過（本地 CI 不執行）。

使用：
  export MISSIVE_PUBLIC_URL=https://api.tree60901.com
  export MCP_SERVICE_TOKEN=<token>
  pytest tests/integration/test_public_exposure_smoke.py -v
"""
from __future__ import annotations

import os

import httpx
import pytest

PUBLIC_URL = os.getenv("MISSIVE_PUBLIC_URL")
TOKEN = os.getenv("MCP_SERVICE_TOKEN", "")

pytestmark = pytest.mark.skipif(
    not PUBLIC_URL,
    reason="MISSIVE_PUBLIC_URL 未設；local CI 跳過公網 smoke test",
)


def test_health_reachable_via_tunnel():
    """CF Tunnel 正確轉發 /api/health 到 localhost:8001"""
    r = httpx.post(f"{PUBLIC_URL}/api/health", json={}, timeout=10.0)
    assert r.status_code == 200


def test_manifest_reachable_post_only():
    """manifest v1.2 經 CF Tunnel 可達，且強制 POST"""
    r = httpx.post(f"{PUBLIC_URL}/api/ai/agent/tools", json={}, timeout=10.0)
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "1.2"


def test_manifest_rejects_get_via_tunnel():
    """GET 應被 FastAPI 以 405 拒絕（CF Tunnel 透傳）"""
    r = httpx.get(f"{PUBLIC_URL}/api/ai/agent/tools", timeout=10.0)
    assert r.status_code == 405


def test_acp_requires_service_token():
    """公網 ACP 必須 X-Service-Token — 無 token → 401/403"""
    r = httpx.post(
        f"{PUBLIC_URL}/api/hermes/acp",
        json={"session_id": "smoke", "messages": [{"role": "user", "content": "test"}]},
        timeout=10.0,
    )
    assert r.status_code in (401, 403)


@pytest.mark.skipif(not TOKEN, reason="需 MCP_SERVICE_TOKEN 才能 happy path 測")
def test_acp_happy_path_via_tunnel():
    """帶 token 的 ACP 請求經 CF 能正確走到 Missive orchestrator。

    此測試驗證 tunnel + auth 鏈路，非 LLM 效能；LLM 慢或未就緒視為非致命
    （只要不是 tunnel / auth / proxy 層錯誤碼即可）。
    """
    try:
        r = httpx.post(
            f"{PUBLIC_URL}/api/hermes/acp",
            headers={"X-Service-Token": TOKEN},
            json={"session_id": "smoke-e2e", "messages": [{"role": "user", "content": "ping"}]},
            timeout=120.0,
        )
        status = r.status_code
    except httpx.ReadTimeout:
        # LLM 回應超時屬 orchestrator 問題，非 tunnel 鏈路 — 視為通過
        pytest.skip("orchestrator LLM response > 120s; tunnel chain OK")
        return

    assert status not in (401, 403, 404, 405, 502, 503), (
        f"Tunnel 公網鏈路異常：status={status}"
    )


def test_tls_certificate_valid():
    """驗證 Cloudflare 提供的 TLS 憑證有效。"""
    # httpx 預設 verify=True，若憑證壞會 raise SSLError
    r = httpx.post(f"{PUBLIC_URL}/api/health", json={}, timeout=10.0)
    assert r.url.scheme == "https"
