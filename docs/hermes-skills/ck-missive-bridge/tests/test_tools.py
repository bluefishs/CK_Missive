"""
ck-missive-bridge v2.0 — tools.py 回歸測試 scaffold。

涵蓋範圍（最高風險路徑優先）：
  - _post_with_retry: 5xx 觸發重試、4xx 不重試、timeout 重試
  - _make_handler: 路徑參數 {id} 替換、HTTP 錯誤碼 → 中文訊息 mapping
  - register_all: manifest 不可達時 fallback 到 _STATIC_TOOLS
  - _check_missive_up: GET /api/health 200 視為 up；ConnectError 視為 down

未涵蓋（後續擴充）：
  - 真實 Missive 容器連通（由 CK_Missive 側的 e2e 腳本負責）
  - skill 註冊至真正 Hermes registry（需 hermes-agent dev install）

執行：
    python -m pytest tests/ -q        # 全部
    python -m pytest tests/test_tools.py::test_retry_on_5xx -q   # 單題
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

import tools as t  # noqa: E402  — conftest 已 sys.path 注入


def _resp(status: int, json_body=None, text: str = "") -> httpx.Response:
    """httpx.Response helper — 附上 request 物件，讓 raise_for_status() 可正常運作。"""
    req = httpx.Request("POST", "http://test/endpoint")
    if json_body is not None:
        return httpx.Response(status, json=json_body, request=req)
    return httpx.Response(status, text=text, request=req)


# ──────────────────────────────────────────────────────────
# _post_with_retry
# ──────────────────────────────────────────────────────────

def _mock_client(responses):
    """回傳 context-manager friendly client mock，依序吐 responses。"""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.post = MagicMock(side_effect=responses)
    return client


def test_retry_on_5xx_then_success(monkeypatch):
    responses = [
        _resp(502, text="bad gateway"),
        _resp(200, json_body={"ok": True}),
    ]
    with patch.object(t.httpx, "Client", return_value=_mock_client(responses)):
        monkeypatch.setattr(t, "MAX_RETRIES", 1)
        r = t._post_with_retry("http://x/y", {}, {})
    assert r.status_code == 200


def test_no_retry_on_4xx(monkeypatch):
    responses = [_resp(404, json_body={"error": "not found"})]
    with patch.object(t.httpx, "Client", return_value=_mock_client(responses)):
        monkeypatch.setattr(t, "MAX_RETRIES", 3)
        r = t._post_with_retry("http://x/y", {}, {})
    assert r.status_code == 404


def test_timeout_triggers_retry(monkeypatch):
    responses = [httpx.TimeoutException("read timeout"), _resp(200, json_body={"ok": True})]
    with patch.object(t.httpx, "Client", return_value=_mock_client(responses)):
        monkeypatch.setattr(t, "MAX_RETRIES", 1)
        monkeypatch.setattr(t.time, "sleep", lambda _s: None)  # 加速測試
        r = t._post_with_retry("http://x/y", {}, {})
    assert r.status_code == 200


# ──────────────────────────────────────────────────────────
# _make_handler — URL 路徑參數替換
# ──────────────────────────────────────────────────────────

def test_path_param_substitution(monkeypatch):
    captured = {}

    def fake_post(url, headers, payload, retries=1):
        captured["url"] = url
        return _resp(200, json_body={"ok": True})


    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler("project_detail")  # endpoint 含 {id}
    result = handler({"id": "P2024-001"}, session_id="s", channel="web")
    assert "/projects/P2024-001/detail" in captured["url"]
    assert json.loads(result) == {"ok": True}


# ──────────────────────────────────────────────────────────
# _make_handler — HTTP 錯誤碼訊息映射
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("status,expected_keyword", [
    (401, "認證失效"),
    (403, "無權限"),
    (404, "查無此資料"),
    (500, "後端暫時異常"),
    (504, "逾時"),
])
def test_http_error_mapping(monkeypatch, status, expected_keyword):
    def fake_post(url, headers, payload, retries=1):
        return _resp(status, text="err")

    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler("dispatch_search")
    result_json = json.loads(handler({"question": "q"}, session_id="s"))
    assert result_json["error"] == "http"
    assert result_json["status"] == status
    assert expected_keyword in result_json["message"]


# ──────────────────────────────────────────────────────────
# register_all — manifest 失敗時 fallback
# ──────────────────────────────────────────────────────────

def test_register_all_fallback_to_static(monkeypatch):
    def fail_manifest():
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(t, "_fetch_manifest", fail_manifest)

    registry = MagicMock()
    count = t.register_all(registry)

    assert count == len(t._STATIC_TOOLS)
    assert registry.register.call_count == len(t._STATIC_TOOLS)
    # 檢查註冊名稱前綴
    first_call = registry.register.call_args_list[0]
    assert first_call.kwargs["name"].startswith("missive_")
    assert first_call.kwargs["toolset"] == "ck_missive"


def test_register_all_uses_manifest(monkeypatch):
    monkeypatch.setattr(t, "_fetch_manifest", lambda: {
        "tools": [
            {"name": "custom_tool", "description": "d", "inputSchema": {}},
            {"name": "custom_tool_2", "description": "d2", "inputSchema": {}},
        ]
    })
    registry = MagicMock()
    count = t.register_all(registry)
    assert count == 2
    names = [c.kwargs["name"] for c in registry.register.call_args_list]
    assert names == ["missive_custom_tool", "missive_custom_tool_2"]


# ──────────────────────────────────────────────────────────
# _check_missive_up — health probe
# ──────────────────────────────────────────────────────────

def test_check_up_ok(monkeypatch):
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get = MagicMock(return_value=_resp(200, text="ok"))

    with patch.object(t.httpx, "Client", return_value=client):
        assert t._check_missive_up() is True


def test_check_up_falls_back_to_post_on_405(monkeypatch):
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get = MagicMock(return_value=_resp(405, text="Method Not Allowed"))
    client.post = MagicMock(return_value=_resp(200, text="ok"))

    with patch.object(t.httpx, "Client", return_value=client):
        # 405 已符合 up 判定（根據 _check_missive_up 實作）
        assert t._check_missive_up() is True


def test_check_up_connect_error(monkeypatch):
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get = MagicMock(side_effect=httpx.ConnectError("refused"))

    with patch.object(t.httpx, "Client", return_value=client):
        assert t._check_missive_up() is False


# ──────────────────────────────────────────────────────────
# v6.6 Phase C (A2 read-only): 觀測坤哥內在狀態的 3 個 tools
# ──────────────────────────────────────────────────────────

def test_endpoint_map_includes_a2_readonly_tools():
    """3 個 A2 read-only tool 都該在 _TOOL_ENDPOINT_MAP 註冊正確 endpoint。"""
    assert t._TOOL_ENDPOINT_MAP["get_memory_status"] == "/api/ai/memory/jobs"
    assert t._TOOL_ENDPOINT_MAP["get_evolution_journal"] == "/api/ai/agent/evolution/journal"
    assert t._TOOL_ENDPOINT_MAP["query_graph_unified"] == "/api/v1/ai/graph/unified-search"


def test_static_tools_includes_a2_readonly_tools():
    """3 個 A2 read-only tool 都該在 _STATIC_TOOLS（manifest 不可達時的 fallback）。"""
    names = {tool["name"] for tool in t._STATIC_TOOLS}
    assert "get_memory_status" in names
    assert "get_evolution_journal" in names
    assert "query_graph_unified" in names


def test_a2_tools_have_required_fields():
    """3 個 A2 tool 結構合法（name + description + inputSchema）。"""
    a2 = {"get_memory_status", "get_evolution_journal", "query_graph_unified"}
    for tool in t._STATIC_TOOLS:
        if tool["name"] not in a2:
            continue
        assert isinstance(tool["description"], str) and len(tool["description"]) >= 10
        assert "inputSchema" in tool
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema


def test_get_memory_status_handler_routes_to_correct_endpoint(monkeypatch):
    """get_memory_status handler POST 到 /api/ai/memory/jobs。"""
    captured = {}

    def fake_post(url, headers, payload, retries=1):
        captured["url"] = url
        return _resp(200, json_body={"data": {"jobs": [], "summary": {"total": 0}}})

    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler("get_memory_status")
    handler({}, session_id="s")
    assert captured["url"].endswith("/api/ai/memory/jobs")


def test_get_evolution_journal_handler_routes_correctly(monkeypatch):
    """get_evolution_journal handler POST 到 /api/ai/agent/evolution/journal。"""
    captured = {}

    def fake_post(url, headers, payload, retries=1):
        captured["url"] = url
        captured["payload"] = payload
        return _resp(200, json_body={"data": []})

    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler("get_evolution_journal")
    handler({"limit": 30}, session_id="s")
    assert captured["url"].endswith("/api/ai/agent/evolution/journal")
    assert captured["payload"]["limit"] == 30


def test_query_graph_unified_handler_routes_correctly(monkeypatch):
    """query_graph_unified handler POST 到 /api/v1/ai/graph/unified-search。"""
    captured = {}

    def fake_post(url, headers, payload, retries=1):
        captured["url"] = url
        captured["payload"] = payload
        return _resp(200, json_body={"results": []})

    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler("query_graph_unified")
    handler({"query": "派工糾紛"}, session_id="s")
    assert captured["url"].endswith("/api/v1/ai/graph/unified-search")
    assert captured["payload"]["query"] == "派工糾紛"


def test_register_all_includes_a2_when_fallback(monkeypatch):
    """fallback 到 _STATIC_TOOLS 時 register count 含 A2 tool。"""
    monkeypatch.setattr(t, "_fetch_manifest", lambda: (_ for _ in ()).throw(httpx.ConnectError("x")))
    registry = MagicMock()
    count = t.register_all(registry)
    assert count == len(t._STATIC_TOOLS)
    names = [c.kwargs["name"] for c in registry.register.call_args_list]
    assert "missive_get_memory_status" in names
    assert "missive_get_evolution_journal" in names
    assert "missive_query_graph_unified" in names


# ──────────────────────────────────────────────────────────
# v6.7 E5: A2 read-only 延伸 — patterns/proposals/crystals 3 list tools
# ──────────────────────────────────────────────────────────

def test_endpoint_map_includes_memory_list_tools():
    """3 個 list tool 都該在 _TOOL_ENDPOINT_MAP 註冊正確 endpoint。"""
    assert t._TOOL_ENDPOINT_MAP["memory_patterns_list"] == "/api/ai/memory/patterns/list"
    assert t._TOOL_ENDPOINT_MAP["memory_proposals_list"] == "/api/ai/memory/proposals/list"
    assert t._TOOL_ENDPOINT_MAP["memory_crystals_list"] == "/api/ai/memory/crystals/list"


def test_static_tools_includes_memory_list_tools():
    """3 個 list tool 都該在 _STATIC_TOOLS。"""
    names = {tool["name"] for tool in t._STATIC_TOOLS}
    assert "memory_patterns_list" in names
    assert "memory_proposals_list" in names
    assert "memory_crystals_list" in names


def test_memory_list_tools_have_pagination_params():
    """3 個 list tool 都該支援 limit + offset 分頁參數。"""
    list_names = {"memory_patterns_list", "memory_proposals_list", "memory_crystals_list"}
    for tool in t._STATIC_TOOLS:
        if tool["name"] not in list_names:
            continue
        props = tool["inputSchema"]["properties"]
        assert "limit" in props
        assert "offset" in props
        # 預設值合理
        assert props["limit"].get("default", 0) > 0
        assert props["offset"].get("default", 0) == 0


@pytest.mark.parametrize("tool_name,expected_path", [
    ("memory_patterns_list", "/api/ai/memory/patterns/list"),
    ("memory_proposals_list", "/api/ai/memory/proposals/list"),
    ("memory_crystals_list", "/api/ai/memory/crystals/list"),
])
def test_memory_list_handler_routes_correctly(monkeypatch, tool_name, expected_path):
    """3 個 list handler 各自 POST 到正確 endpoint，args 完整傳遞。"""
    captured = {}

    def fake_post(url, headers, payload, retries=1):
        captured["url"] = url
        captured["payload"] = payload
        return _resp(200, json_body={"data": []})

    monkeypatch.setattr(t, "_post_with_retry", fake_post)
    handler = t._make_handler(tool_name)
    handler({"limit": 30, "offset": 10}, session_id="s")
    assert captured["url"].endswith(expected_path)
    assert captured["payload"]["limit"] == 30
    assert captured["payload"]["offset"] == 10


def test_register_all_includes_memory_list_when_fallback(monkeypatch):
    """fallback 註冊時 3 個 list tool 也該進。"""
    monkeypatch.setattr(t, "_fetch_manifest", lambda: (_ for _ in ()).throw(httpx.ConnectError("x")))
    registry = MagicMock()
    t.register_all(registry)
    names = [c.kwargs["name"] for c in registry.register.call_args_list]
    assert "missive_memory_patterns_list" in names
    assert "missive_memory_proposals_list" in names
    assert "missive_memory_crystals_list" in names
