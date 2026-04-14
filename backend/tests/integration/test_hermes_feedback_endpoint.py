# -*- coding: utf-8 -*-
"""Hermes Feedback 端點整合測試（L4 學習閉環）。

    POST /api/hermes/feedback
      Headers: X-Service-Token
      Body: HermesFeedback
      Returns: 202 Accepted | 401/403/422
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "tok")
    from app.api.endpoints.hermes_acp import router
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_feedback_requires_token(client):
    r = client.post("/api/hermes/feedback", json={
        "session_id": "s", "skill_name": "x",
        "outcome": "success", "latency_ms": 1,
    })
    assert r.status_code in (401, 403)


def test_feedback_accepted(client):
    fake = AsyncMock(return_value=None)
    with patch("app.api.endpoints.hermes_acp.persist_feedback", new=fake):
        r = client.post(
            "/api/hermes/feedback",
            headers={"X-Service-Token": "tok"},
            json={
                "session_id": "s1",
                "skill_name": "missive_document_search",
                "outcome": "success",
                "latency_ms": 250,
                "tools_used": ["document_search"],
                "user_satisfaction": 0.9,
            },
        )
    assert r.status_code == 202
    body = r.json()
    assert body["accepted"] is True
    assert body["session_id"] == "s1"
    fake.assert_awaited_once()


def test_feedback_422_on_bad_outcome(client):
    r = client.post(
        "/api/hermes/feedback",
        headers={"X-Service-Token": "tok"},
        json={"session_id": "s", "skill_name": "x",
              "outcome": "invalid", "latency_ms": 1},
    )
    assert r.status_code == 422


def test_feedback_swallows_persist_error(client):
    """persist 失敗不該導致 5xx — L4 異步閉環容錯。"""
    with patch(
        "app.api.endpoints.hermes_acp.persist_feedback",
        new=AsyncMock(side_effect=RuntimeError("DB down")),
    ):
        r = client.post(
            "/api/hermes/feedback",
            headers={"X-Service-Token": "tok"},
            json={"session_id": "s", "skill_name": "x",
                  "outcome": "failure", "latency_ms": 10},
        )
    # 仍回 202（persist 是 fire-and-forget）
    assert r.status_code == 202
    assert r.json()["accepted"] is True
