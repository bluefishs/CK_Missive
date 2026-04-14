# -*- coding: utf-8 -*-
"""Hermes ACP Endpoint 整合測試（ADR-0014）。

端點合約：
  POST /api/hermes/acp
    Headers: X-Service-Token (必要)
    Body: AcpRequest
    Returns: AcpResponse (200) | error (401/422/500)
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token-xyz")
    monkeypatch.setenv("SHADOW_ENABLED", "0")  # 測試期關閉 shadow 寫入

    from app.api.endpoints.hermes_acp import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_acp_requires_service_token(app_client):
    r = app_client.post("/api/hermes/acp", json={
        "session_id": "s1",
        "messages": [{"role": "user", "content": "q"}],
    })
    assert r.status_code in (401, 403)


def test_acp_rejects_bad_token(app_client):
    r = app_client.post(
        "/api/hermes/acp",
        headers={"X-Service-Token": "wrong"},
        json={"session_id": "s1", "messages": [{"role": "user", "content": "q"}]},
    )
    assert r.status_code in (401, 403)


def test_acp_rejects_empty_messages(app_client):
    r = app_client.post(
        "/api/hermes/acp",
        headers={"X-Service-Token": "test-token-xyz"},
        json={"session_id": "s1", "messages": []},
    )
    assert r.status_code == 422


def test_acp_happy_path(app_client):
    async def fake_process(req, headers):
        from app.schemas.hermes_acp import AcpResponse
        return AcpResponse(
            session_id=req.session_id,
            answer="fake answer",
            sources=[],
            tools_used=["document_search"],
            latency_ms=123,
        )

    with patch("app.api.endpoints.hermes_acp.process_acp", new=fake_process):
        r = app_client.post(
            "/api/hermes/acp",
            headers={"X-Service-Token": "test-token-xyz"},
            json={
                "session_id": "hermes-abc",
                "messages": [{"role": "user", "content": "案號 CK2026001 狀態"}],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "hermes-abc"
    assert body["answer"] == "fake answer"
    assert body["tools_used"] == ["document_search"]
    assert body["latency_ms"] == 123


def test_acp_propagates_hermes_session_header(app_client):
    captured = {}

    async def fake_process(req, headers):
        from app.schemas.hermes_acp import AcpResponse
        captured["hermes_session"] = headers.get("x-hermes-session")
        captured["provider"] = headers.get("x-provider")
        return AcpResponse(
            session_id=req.session_id, answer="ok", latency_ms=1,
        )

    with patch("app.api.endpoints.hermes_acp.process_acp", new=fake_process):
        app_client.post(
            "/api/hermes/acp",
            headers={
                "X-Service-Token": "test-token-xyz",
                "X-Hermes-Session": "hermes-sid-999",
                "X-Provider": "gemma-hermes",
            },
            json={"session_id": "s", "messages": [{"role": "user", "content": "q"}]},
        )
    assert captured["hermes_session"] == "hermes-sid-999"
    assert captured["provider"] == "gemma-hermes"


def test_acp_error_handling(app_client):
    async def broken_process(req, headers):
        raise RuntimeError("boom")

    with patch("app.api.endpoints.hermes_acp.process_acp", new=broken_process):
        r = app_client.post(
            "/api/hermes/acp",
            headers={"X-Service-Token": "test-token-xyz"},
            json={"session_id": "s", "messages": [{"role": "user", "content": "q"}]},
        )
    assert r.status_code == 500
    body = r.json()
    assert body.get("error_code") or "error" in str(body).lower()
