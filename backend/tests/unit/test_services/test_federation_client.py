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

    def test_no_env_means_not_available(self):
        with patch.dict("os.environ", {}, clear=True):
            client = FederationClient()
            assert client.is_available("openclaw") is False

    def test_with_env_is_available(self):
        with patch.dict("os.environ", {"OPENCLAW_URL": "http://localhost:3001"}):
            client = FederationClient()
            assert client.is_available("openclaw") is True

    def test_unknown_system_not_available(self):
        client = FederationClient()
        assert client.is_available("nonexistent") is False

    def test_list_available_systems_with_env(self):
        with patch.dict("os.environ", {"OPENCLAW_URL": "http://localhost:3001"}):
            client = FederationClient()
            systems = client.list_available_systems()
            assert len(systems) >= 1
            openclaw = next(s for s in systems if s["id"] == "openclaw")
            assert openclaw["available"] is True
            assert openclaw["name"] == "CK_OpenClaw"

    def test_list_systems_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            client = FederationClient()
            systems = client.list_available_systems()
            openclaw = next(s for s in systems if s["id"] == "openclaw")
            assert openclaw["available"] is False


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
    async def test_unconfigured_system_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            client = FederationClient()
            result = await client.query_external("openclaw", "hello")
            assert result["success"] is False
            assert "OPENCLAW_URL" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_query(self):
        mock_inst = _make_mock_client(200, {
            "success": True,
            "answer": "OpenClaw has 30+ channels",
            "tools_used": ["list_channels"],
        })

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://localhost:3001",
            "MCP_SERVICE_TOKEN": "test-token",
        }):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "What channels?")

        assert result["success"] is True
        assert result["system"] == "openclaw"
        assert "30+" in result["answer"]
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_http_error_returns_error(self):
        mock_inst = _make_mock_client(500)

        with patch.dict("os.environ", {"OPENCLAW_URL": "http://localhost:3001"}):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "test")

        assert result["success"] is False
        assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_error_returns_error(self):
        mock_inst = _make_mock_client(side_effect=ConnectionError("refused"))

        with patch.dict("os.environ", {"OPENCLAW_URL": "http://localhost:3001"}):
            client = FederationClient()

        with patch("app.services.ai.federation_client.httpx") as mock_httpx:
            mock_httpx.AsyncClient.return_value = mock_inst
            result = await client.query_external("openclaw", "test")

        assert result["success"] is False
        assert "ConnectionError" in result["error"]

    @pytest.mark.asyncio
    async def test_token_sent_in_header(self):
        mock_inst = _make_mock_client(200, {"success": True, "answer": "ok"})

        with patch.dict("os.environ", {
            "OPENCLAW_URL": "http://localhost:3001",
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
