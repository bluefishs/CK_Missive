"""
Unit tests for FederationClient.

Tests cover:
- System availability checks
- Listing available systems
- Error handling for unconfigured systems
- Successful query flow (mocked httpx)
- Timeout / connection error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.federation_client import FederationClient


class TestFederationClientAvailability:
    """Test system availability and listing."""

    def test_no_env_uses_default_url(self):
        """Without OPENCLAW_URL env, should fall back to default_url."""
        with patch.dict("os.environ", {}, clear=True):
            client = FederationClient()
            assert client.is_available("openclaw") is True

    def test_with_env_is_available(self):
        with patch.dict("os.environ", {"OPENCLAW_URL": "http://openclaw:18789"}):
            client = FederationClient()
            assert client.is_available("openclaw") is True

    def test_unknown_system_not_available(self):
        client = FederationClient()
        assert client.is_available("nonexistent") is False

    def test_list_available_systems_with_env(self):
        with patch.dict("os.environ", {"OPENCLAW_URL": "http://openclaw:18789"}):
            client = FederationClient()
            systems = client.list_available_systems()
            assert len(systems) >= 1
            openclaw = next(s for s in systems if s["id"] == "openclaw")
            assert openclaw["available"] is True
            assert openclaw["name"] == "CK_OpenClaw"

    def test_list_systems_default_url_available(self):
        """Without env vars, openclaw should still be available via default_url."""
        with patch.dict("os.environ", {}, clear=True):
            client = FederationClient()
            systems = client.list_available_systems()
            openclaw = next(s for s in systems if s["id"] == "openclaw")
            assert openclaw["available"] is True


def _make_mock_client(response_status=200, response_json=None, side_effect=None):
    """Helper to build an async context manager mock for httpx.AsyncClient."""
    mock_response = MagicMock()
    mock_response.status_code = response_status
    mock_response.json.return_value = response_json or {}
    mock_response.text = f"HTTP {response_status}"

    mock_inst = AsyncMock()
    if side_effect:
        mock_inst.post = AsyncMock(side_effect=side_effect)
    else:
        mock_inst.post = AsyncMock(return_value=mock_response)

    mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
    mock_inst.__aexit__ = AsyncMock(return_value=False)
    return mock_inst


class TestFederationClientQuery:
    """Test query_external method."""

    @pytest.mark.asyncio
    async def test_unknown_system_returns_error(self):
        client = FederationClient()
        result = await client.query_external("nonexistent", "hello")
        assert result["success"] is False
        assert "未知" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_system_id_returns_error(self):
        """Querying a system not in _SYSTEM_REGISTRY should fail."""
        client = FederationClient()
        result = await client.query_external("nonexistent_system", "hello")
        assert result["success"] is False
        assert "未知" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_query(self):
        """Test successful query with Schema v1.0 nested response format."""
        mock_inst = _make_mock_client(200, {
            "success": True,
            "agent_id": "openclaw",
            "action": "reason",
            "result": {
                "answer": "OpenClaw has 30+ channels",
                "tools_used": ["list_channels"],
                "model": "openclaw",
            },
            "meta": {
                "latency_ms": 1200,
                "request_id": "reason_test",
            },
            "timestamp": "2026-03-20T10:00:00Z",
        })

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://openclaw:18789",
            "MCP_SERVICE_TOKEN": "test-token",
        }):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "What channels?")

        assert result["success"] is True
        assert result["system"] == "openclaw"
        assert "30+" in result["answer"]
        assert result["latency_ms"] == 1200

    @pytest.mark.asyncio
    async def test_http_error_returns_error(self):
        mock_inst = _make_mock_client(500)

        with patch.dict("os.environ", {"OPENCLAW_URL": "http://openclaw:18789"}):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "test")

        assert result["success"] is False
        assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_error_returns_error(self):
        mock_inst = _make_mock_client(side_effect=ConnectionError("refused"))

        with patch.dict("os.environ", {"OPENCLAW_URL": "http://openclaw:18789"}):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "test")

        assert result["success"] is False
        assert "ConnectionError" in result["error"]

    @pytest.mark.asyncio
    async def test_schema_v1_payload_format(self):
        """Test that query_external sends Schema v1.0 envelope format."""
        mock_inst = _make_mock_client(200, {
            "success": True,
            "result": {"answer": "ok"},
            "meta": {"latency_ms": 100},
        })

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://openclaw:18789",
            "MCP_SERVICE_TOKEN": "test-token",
        }):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            await client.query_external("openclaw", "test", context={"doc_id": "123"})

        call_kwargs = mock_inst.post.call_args
        payload = call_kwargs.kwargs.get("json", {})
        assert payload["agent_id"] == "ck_missive"
        assert payload["action"] == "reason"
        assert payload["payload"]["question"] == "test"
        assert payload["payload"]["context"] == {"doc_id": "123"}
        assert "timestamp" in payload
        assert "session_id" in payload

    @pytest.mark.asyncio
    async def test_error_response_parsing(self):
        """Test Schema v1.0 error response parsing."""
        mock_inst = _make_mock_client(200, {
            "success": False,
            "result": None,
            "error": {"code": "INTERNAL_ERROR", "message": "LLM timeout"},
            "meta": {"latency_ms": 30000},
        })

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://openclaw:18789",
            "MCP_SERVICE_TOKEN": "test-token",
        }):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "test")

        assert result["success"] is False
        assert result["error"] == "LLM timeout"
        assert result["answer"] == ""

    @pytest.mark.asyncio
    async def test_token_sent_in_header(self):
        mock_inst = _make_mock_client(200, {
            "success": True,
            "result": {"answer": "ok"},
            "meta": {"latency_ms": 50},
        })

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://openclaw:18789",
            "MCP_SERVICE_TOKEN": "my-secret",
        }):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            await client.query_external("openclaw", "test")

        call_kwargs = mock_inst.post.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers.get("X-Service-Token") == "my-secret"

    @pytest.mark.asyncio
    async def test_url_trailing_slash_stripped(self):
        """URL trailing slash should be stripped to avoid double slashes."""
        mock_inst = _make_mock_client(200, {"success": True, "answer": "ok"})

        with patch.dict("os.environ", {"OPENCLAW_URL": "http://localhost:3001/"}):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            await client.query_external("openclaw", "test")

        call_args = mock_inst.post.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "//" not in url.replace("http://", "")
