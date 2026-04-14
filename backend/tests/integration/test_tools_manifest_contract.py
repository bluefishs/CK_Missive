# -*- coding: utf-8 -*-
"""
Tools Manifest Public Contract 測試 — ADR-0014 Hermes 整合依賴此端點。

保護 public contract：任何 breaking change 需走 ADR + 30 天 deprecation。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints.ai.tools_manifest import TOOL_MANIFEST, router


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/ai")
    return TestClient(app)


def test_manifest_version_bumped():
    """manifest v1.2 起須含 compat/endpoints/auth/hermes 區塊（ADR-0014）。"""
    assert TOOL_MANIFEST["version"] == "1.2"
    assert "compat" in TOOL_MANIFEST
    assert "endpoints" in TOOL_MANIFEST
    assert "auth" in TOOL_MANIFEST
    assert "hermes" in TOOL_MANIFEST, "v1.2: hermes block must advertise ACP/feedback paths"


def test_hermes_block_advertises_acp_and_feedback():
    """Hermes 可以從 manifest 自發現 ACP 入口與 feedback 回寫入口。"""
    hermes = TOOL_MANIFEST["hermes"]
    assert hermes["acp_endpoint"] == "/api/hermes/acp"
    assert hermes["feedback_endpoint"] == "/api/hermes/feedback"
    assert hermes["min_hermes_version"]
    assert hermes["tool_prefix"] == "missive_"


def test_hermes_compat_declared():
    """Hermes 最低版本要求必須宣告。"""
    assert TOOL_MANIFEST["compat"]["hermes_agent"].startswith(">=")


def test_auth_mechanism():
    """對外 tool 呼叫必須走 service token。"""
    auth = TOOL_MANIFEST["auth"]
    assert auth["type"] == "bearer"
    assert auth["header"] == "X-Service-Token"
    assert auth["env_var"] == "MCP_SERVICE_TOKEN"


def test_all_tools_have_endpoint_mapping():
    """每個 tool 都必須在 endpoints map 有對應路徑（否則 Hermes 無從呼叫）。"""
    tool_names = {t["name"] for t in TOOL_MANIFEST["tools"]}
    mapped = set(TOOL_MANIFEST["endpoints"].keys())
    missing = tool_names - mapped
    assert not missing, f"tools missing endpoint mapping: {missing}"


def test_tool_schema_shape():
    """每 tool 須具備 name/description/inputSchema/category/permission。"""
    for tool in TOOL_MANIFEST["tools"]:
        for key in ("name", "description", "inputSchema", "category", "permission"):
            assert key in tool, f"{tool.get('name')} missing {key}"
        assert tool["inputSchema"]["type"] == "object"
        assert "properties" in tool["inputSchema"]


def test_no_breaking_tool_removals():
    """Hermes bridge 依賴這些 tool；移除前必須走 ADR。"""
    required = {
        "document_search",
        "dispatch_search",
        "entity_search",
        "entity_detail",
        "semantic_similar",
        "system_statistics",
        "federated_search",
        "federated_contribute",
    }
    present = {t["name"] for t in TOOL_MANIFEST["tools"]}
    missing = required - present
    assert not missing, (
        f"critical tools removed without ADR: {missing}. "
        f"See docs/adr/0014-hermes-replace-openclaw.md public contract section."
    )


def test_manifest_endpoint_returns_200(client):
    """POST-only per security policy（GET 應回 405）。"""
    resp = client.post("/api/ai/agent/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "1.2"
    assert body["serverName"] == "ck_missive"


def test_manifest_rejects_get(client):
    """GET 被禁用（資安政策：所有端點採 POST）。"""
    resp = client.get("/api/ai/agent/tools")
    assert resp.status_code == 405
