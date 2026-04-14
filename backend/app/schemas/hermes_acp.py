# -*- coding: utf-8 -*-
"""
Hermes ACP (Agent Communication Protocol) schemas.

供 ``/api/hermes/acp`` 端點使用；Missive 在 ADR-0014 架構下扮演 ACP server，
接受 Hermes Agent 發來的 query 並回傳統一格式回應。

參考：hermes-acp adapter（NousResearch/hermes-agent 內建 entry point）
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


AcpRole = Literal["user", "assistant", "system", "tool"]


class AcpMessage(BaseModel):
    role: AcpRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class AcpRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    messages: List[AcpMessage] = Field(..., min_length=1)
    allowed_tools: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("session_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id must not be empty")
        return v


class AcpResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    latency_ms: int = Field(..., ge=0)
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


FeedbackOutcome = Literal["success", "failure", "timeout", "partial"]


class HermesFeedback(BaseModel):
    """Hermes skill 執行回饋（L4 學習閉環）。"""
    session_id: str = Field(..., min_length=1)
    skill_name: str = Field(..., min_length=1)
    outcome: FeedbackOutcome
    latency_ms: int = Field(..., ge=0)
    tools_used: List[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    user_satisfaction: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
