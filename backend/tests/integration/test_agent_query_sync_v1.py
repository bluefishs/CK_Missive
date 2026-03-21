# -*- coding: utf-8 -*-
"""
P1-b-2c: agent_query_sync 雙格式相容測試

測試 v0 (legacy) 與 v1 (Schema v1.0) 格式的請求/回應。
覆蓋範圍:
  - v0 正常查詢 + 回應格式
  - v1 正常查詢 + 信封回應格式
  - v1 缺少 payload.question → 422
  - v0/v1 agent 錯誤 → 各自格式的錯誤回應
  - v0/v1 逾時 → 各自格式的逾時回應
  - 認證失敗 → 401/403
  - detect_request_format 單元測試

Version: 1.0.0
Created: 2026-03-20
"""

import asyncio
import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.schemas.ai.rag import detect_request_format


# ============================================================
# Fixtures
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def service_client():
    """HTTP client with MCP_SERVICE_TOKEN set for auth.
    Resets rate limiter storage before each test to avoid 429.
    """
    os.environ["MCP_SERVICE_TOKEN"] = "test-secret-token"

    from main import app
    from app.db.database import engine as app_engine
    from app.core.rate_limiter import limiter

    # 重置 rate limiter 計數，避免跨測試 429
    try:
        limiter.reset()
    except Exception:
        # 某些 storage backend 可能不支援 reset
        if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
            limiter._storage.reset()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await app_engine.dispose()
    os.environ.pop("MCP_SERVICE_TOKEN", None)


@pytest.fixture
def auth_headers():
    return {"X-Service-Token": "test-secret-token"}


def _mock_stream_query(answer="測試回答", sources=None, tools=None):
    """建立 mock stream_query，回傳預設的 SSE 事件。"""
    sources = sources or [{"type": "doc", "id": "D-001", "relevance": 0.9}]
    tools = tools or ["doc_search"]

    async def stream_query(question, history=None, session_id=None):
        events = [
            f'data: {json.dumps({"type": "token", "token": answer})}',
            f'data: {json.dumps({"type": "sources", "sources": sources})}',
        ]
        for t in tools:
            events.append(f'data: {json.dumps({"type": "tool_result", "tool": t})}')
        events.append(f'data: {json.dumps({"type": "done", "latency_ms": 123})}')

        for e in events:
            yield e

    return stream_query


def _mock_stream_query_error(error_msg="Agent 內部錯誤"):
    """建立回傳錯誤的 mock stream_query。"""
    async def stream_query(question, history=None, session_id=None):
        yield f'data: {json.dumps({"type": "error", "error": error_msg})}'

    return stream_query


def _v0_request_body(question="測試問題", session_id=None):
    """建立 v0 legacy 格式請求。"""
    body = {"question": question}
    if session_id:
        body["session_id"] = session_id
    return body


def _v1_request_body(question="測試問題", agent_id="ck_openclaw", action="query", session_id=None):
    """建立 v1 Schema v1.0 格式請求。"""
    body = {
        "agent_id": agent_id,
        "action": action,
        "payload": {"question": question},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if session_id:
        body["session_id"] = session_id
    return body


# ============================================================
# Unit Tests: detect_request_format
# ============================================================

class TestDetectRequestFormat:
    def test_v0_with_question(self):
        assert detect_request_format({"question": "hello"}) == "v0"

    def test_v0_with_extra_fields(self):
        assert detect_request_format({"question": "hello", "session_id": "abc"}) == "v0"

    def test_v1_full(self):
        data = {
            "agent_id": "ck_openclaw",
            "action": "query",
            "payload": {"question": "hello"},
            "timestamp": "2026-03-20T00:00:00Z",
        }
        assert detect_request_format(data) == "v1"

    def test_v1_missing_timestamp_falls_to_v0(self):
        data = {
            "agent_id": "ck_openclaw",
            "action": "query",
            "payload": {"question": "hello"},
        }
        assert detect_request_format(data) == "v0"

    def test_v1_missing_payload_falls_to_v0(self):
        data = {
            "agent_id": "ck_openclaw",
            "action": "query",
            "timestamp": "2026-03-20T00:00:00Z",
        }
        assert detect_request_format(data) == "v0"

    def test_empty_dict_is_v0(self):
        assert detect_request_format({}) == "v0"


# ============================================================
# Integration Tests: v0 (legacy) format
# ============================================================

@pytest.mark.asyncio
class TestV0Format:
    async def test_v0_success(self, service_client, auth_headers):
        """v0 格式正常查詢 → 扁平 AgentSyncResponse"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query(answer="v0回答")

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v0_request_body("測試問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["answer"] == "v0回答"
        assert "doc_search" in data["tools_used"]
        assert data["latency_ms"] == 123
        # v0 不應有 agent_id / action / result 信封欄位
        assert "agent_id" not in data
        assert "result" not in data

    async def test_v0_agent_error(self, service_client, auth_headers):
        """v0 格式 agent 錯誤 → success=False + error 字串"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query_error("工具執行失敗")

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v0_request_body("會失敗的問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "工具執行失敗" in data["error"]

    async def test_v0_timeout(self, service_client, auth_headers):
        """v0 格式逾時 → success=False + 逾時錯誤"""
        async def slow_stream(question, history=None, session_id=None):
            await asyncio.sleep(999)
            yield 'data: {"type": "done"}'

        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent, patch(
            "app.api.endpoints.ai.agent_query_sync.get_ai_config"
        ) as mock_config:
            instance = MockAgent.return_value
            instance.stream_query = slow_stream
            mock_config.return_value.agent_sync_query_timeout = 0.1

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v0_request_body("逾時問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "逾時" in data["error"]

    async def test_v0_empty_question_rejected(self, service_client, auth_headers):
        """v0 空 question → 422"""
        resp = await service_client.post(
            "/api/ai/agent/query",
            json={"question": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ============================================================
# Integration Tests: v1 (Schema v1.0) format
# ============================================================

@pytest.mark.asyncio
class TestV1Format:
    async def test_v1_success(self, service_client, auth_headers):
        """v1 格式正常查詢 → Schema v1.0 信封回應"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query(answer="v1回答")

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v1_request_body("v1測試問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        # Schema v1.0 信封結構
        assert data["success"] is True
        assert data["agent_id"] == "ck_missive"
        assert data["action"] == "query"
        assert "timestamp" in data
        # result 嵌套
        result = data["result"]
        assert result["answer"] == "v1回答"
        assert "doc_search" in result["tools_used"]
        # meta
        meta = data["meta"]
        assert meta["latency_ms"] == 123
        assert "request_id" in meta

    async def test_v1_reason_action(self, service_client, auth_headers):
        """v1 action=reason 也能正常處理"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query(answer="reason回答")

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v1_request_body("推理問題", action="reason"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["action"] == "reason"

    async def test_v1_missing_question_422(self, service_client, auth_headers):
        """v1 payload 缺少 question → 422 + INVALID_SCHEMA"""
        body = {
            "agent_id": "ck_openclaw",
            "action": "query",
            "payload": {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        resp = await service_client.post(
            "/api/ai/agent/query",
            json=body,
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_SCHEMA"

    async def test_v1_agent_error(self, service_client, auth_headers):
        """v1 格式 agent 錯誤 → 信封錯誤回應"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query_error("推理引擎異常")

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v1_request_body("會失敗的v1問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["agent_id"] == "ck_missive"
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "推理引擎異常" in data["error"]["message"]

    async def test_v1_timeout(self, service_client, auth_headers):
        """v1 格式逾時 → 504 + TIMEOUT"""
        async def slow_stream(question, history=None, session_id=None):
            await asyncio.sleep(999)
            yield 'data: {"type": "done"}'

        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent, patch(
            "app.api.endpoints.ai.agent_query_sync.get_ai_config"
        ) as mock_config:
            instance = MockAgent.return_value
            instance.stream_query = slow_stream
            mock_config.return_value.agent_sync_query_timeout = 0.1

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v1_request_body("逾時v1問題"),
                headers=auth_headers,
            )

        assert resp.status_code == 504
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TIMEOUT"

    async def test_v1_with_session_id(self, service_client, auth_headers):
        """v1 含 session_id → 正確傳遞"""
        with patch(
            "app.services.ai.nemoclaw_agent.NemoClawAgent"
        ) as MockAgent:
            instance = MockAgent.return_value
            instance.stream_query = _mock_stream_query()

            resp = await service_client.post(
                "/api/ai/agent/query",
                json=_v1_request_body("帶session", session_id="sess-123"),
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ============================================================
# Auth Tests (共用)
# ============================================================

@pytest.mark.asyncio
class TestAuth:
    async def test_missing_token_403(self, service_client):
        """未設 token 且非 dev localhost → 403"""
        os.environ.pop("DEVELOPMENT_MODE", None)
        resp = await service_client.post(
            "/api/ai/agent/query",
            json=_v0_request_body("需要認證"),
        )
        assert resp.status_code in (401, 403)

    async def test_wrong_token_401(self, service_client):
        """錯誤 token → 401"""
        resp = await service_client.post(
            "/api/ai/agent/query",
            json=_v0_request_body("錯誤token"),
            headers={"X-Service-Token": "wrong-token"},
        )
        assert resp.status_code == 401

    async def test_invalid_json_422(self, service_client, auth_headers):
        """非法 JSON body → 422"""
        resp = await service_client.post(
            "/api/ai/agent/query",
            content=b"not json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 422
