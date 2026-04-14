# -*- coding: utf-8 -*-
"""Hermes ACP Schema TDD — `/api/hermes/acp` 的請求/回應結構。

ACP (Agent Communication Protocol) 為 Hermes 原生協議。
Missive 扮演 ACP server，接受 Hermes Agent 的 query。
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_acp_request_minimal_shape():
    from app.schemas.hermes_acp import AcpRequest

    req = AcpRequest(
        session_id="hermes-sess-001",
        messages=[{"role": "user", "content": "案號 CK2026001 狀態"}],
    )
    assert req.session_id == "hermes-sess-001"
    assert len(req.messages) == 1


def test_acp_request_requires_at_least_one_message():
    from app.schemas.hermes_acp import AcpRequest

    with pytest.raises(ValidationError):
        AcpRequest(session_id="s", messages=[])


def test_acp_request_session_id_not_empty():
    from app.schemas.hermes_acp import AcpRequest

    with pytest.raises(ValidationError):
        AcpRequest(session_id="", messages=[{"role": "user", "content": "q"}])


def test_acp_message_role_validation():
    from app.schemas.hermes_acp import AcpRequest

    with pytest.raises(ValidationError):
        AcpRequest(
            session_id="s",
            messages=[{"role": "invalid_role", "content": "x"}],
        )


def test_acp_response_shape():
    from app.schemas.hermes_acp import AcpResponse

    resp = AcpResponse(
        session_id="s",
        answer="案號 CK2026001 目前施工中",
        sources=[{"type": "doc", "id": "123"}],
        tools_used=["document_search"],
        latency_ms=420,
    )
    assert resp.answer
    assert resp.latency_ms == 420


def test_acp_response_defaults():
    from app.schemas.hermes_acp import AcpResponse

    resp = AcpResponse(session_id="s", answer="ok", latency_ms=10)
    assert resp.sources == []
    assert resp.tools_used == []


def test_acp_request_optional_tool_hints():
    from app.schemas.hermes_acp import AcpRequest

    req = AcpRequest(
        session_id="s",
        messages=[{"role": "user", "content": "q"}],
        allowed_tools=["document_search", "tender_search"],
    )
    assert req.allowed_tools == ["document_search", "tender_search"]
