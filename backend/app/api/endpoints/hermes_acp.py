# -*- coding: utf-8 -*-
"""
Hermes ACP Endpoint — ADR-0014 深度整合層。

Hermes Agent 透過 ACP (Agent Communication Protocol) 呼叫 Missive：

    POST /api/hermes/acp
      Headers:
        X-Service-Token  (required) — MCP_SERVICE_TOKEN
        X-Hermes-Session (optional) — Hermes 端 session id（寫入 shadow trace）
        X-Provider       (optional) — 覆蓋自動偵測的 provider 標籤
      Body: AcpRequest
      Returns: AcpResponse

職責：
  - 驗證 service token
  - 取最後一則 user message 作為 question
  - 委派 AgentOrchestrator 處理（或被 monkeypatch 測試）
  - 回傳 AcpResponse 並寫入 shadow_logger trace
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import time
from typing import Dict, Mapping

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas.hermes_acp import AcpRequest, AcpResponse, HermesFeedback
from app.services.ai.agent.provider_resolver import resolve_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hermes", tags=["Hermes ACP"])


def _verify_service_token(
    request: Request,
    x_service_token: str = Header(None, alias="X-Service-Token"),
) -> bool:
    current = os.getenv("MCP_SERVICE_TOKEN")
    prev = os.getenv("MCP_SERVICE_TOKEN_PREV")
    if not current:
        raise HTTPException(status_code=403, detail="Service token not configured")
    if not x_service_token:
        raise HTTPException(status_code=401, detail="Missing X-Service-Token")
    provided = x_service_token.encode("utf-8")
    ok = hmac.compare_digest(provided, current.encode("utf-8"))
    if not ok and prev:
        ok = hmac.compare_digest(provided, prev.encode("utf-8"))
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return True


async def process_acp(req: AcpRequest, headers: Mapping[str, str]) -> AcpResponse:
    """預設處理器：呼叫 AgentOrchestrator stream，聚合 tokens。

    測試以 monkeypatch 替換此函式；生產期由 orchestrator 實作。
    """
    from app.services.ai.agent.agent_orchestrator import AgentOrchestrator
    from app.services.sender_context import SenderContext
    from app.db.database import AsyncSessionLocal

    user_msg = next(
        (m for m in reversed(req.messages) if m.role == "user"),
        req.messages[-1],
    )
    question = user_msg.content[:2000]

    sender_ctx = SenderContext(
        user_id=headers.get("x-hermes-user", "hermes"),
        display_name="hermes-agent",
        channel="hermes",
        channel_id=headers.get("x-hermes-session"),
    )

    start = time.monotonic()
    answer_parts: list[str] = []
    tools_used: list[str] = []
    sources: list[dict] = []

    async with AsyncSessionLocal() as db:
        orchestrator = AgentOrchestrator(db)
        async for event in orchestrator.stream_agent_query(
            question=question,
            session_id=req.session_id,
            sender_context=sender_ctx,
        ):
            try:
                data = json.loads(event.replace("data: ", "").strip())
                if data.get("type") == "token":
                    answer_parts.append(data.get("token", ""))
                elif data.get("type") == "tool_use":
                    tools_used.append(data.get("tool", ""))
                elif data.get("type") == "source":
                    sources.append(data.get("source", {}))
            except (ValueError, AttributeError):
                continue

    latency_ms = int((time.monotonic() - start) * 1000)
    return AcpResponse(
        session_id=req.session_id,
        answer="".join(answer_parts) or "（無回應）",
        sources=sources,
        tools_used=tools_used,
        latency_ms=latency_ms,
    )


@router.post("/acp", response_model=AcpResponse)
# Rate limit: 由 SlowAPIMiddleware 統一處理（per-route 裝飾器與 pydantic 回應不相容）
async def hermes_acp_endpoint(
    req: AcpRequest,
    request: Request,
    _: bool = Depends(_verify_service_token),
) -> AcpResponse:
    headers: Dict[str, str] = {k.lower(): v for k, v in request.headers.items()}
    provider = resolve_provider(channel="hermes", headers=headers)
    start = time.monotonic()

    try:
        resp = await process_acp(req, headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ACP processing failed: %s", e, exc_info=True)
        elapsed = int((time.monotonic() - start) * 1000)
        # shadow log the failure (best-effort)
        _fire_and_forget_shadow(
            channel="hermes",
            provider=provider,
            question=req.messages[-1].content,
            answer="",
            success=False,
            latency_ms=elapsed,
            error_code="internal",
            session_id=req.session_id,
            request_id=headers.get("x-hermes-session"),
        )
        return JSONResponse(
            status_code=500,
            content={"session_id": req.session_id, "error_code": "internal", "answer": ""},
        )

    _fire_and_forget_shadow(
        channel="hermes",
        provider=provider,
        question=req.messages[-1].content,
        answer=resp.answer,
        success=True,
        latency_ms=resp.latency_ms,
        tools_used=resp.tools_used,
        sources_count=len(resp.sources),
        session_id=req.session_id,
        request_id=headers.get("x-hermes-session"),
    )
    return resp


def _fire_and_forget_shadow(**kwargs) -> None:
    try:
        from app.services.ai.agent.shadow_logger import is_enabled, log_trace
        if not is_enabled():
            return
        asyncio.create_task(log_trace(**kwargs))
    except Exception:  # noqa: BLE001
        pass


async def persist_feedback(payload: HermesFeedback) -> None:
    """持久化 Hermes skill 回饋到 agent_learning 表（預設 log-only）。

    生產期由 orchestrator 實作；測試以 monkeypatch 替換。
    L4 學習閉環異步執行，失敗不影響 endpoint 回應。
    """
    logger.info(
        "hermes.feedback session=%s skill=%s outcome=%s latency=%dms satisfaction=%s",
        payload.session_id, payload.skill_name, payload.outcome,
        payload.latency_ms, payload.user_satisfaction,
    )


@router.post("/feedback", status_code=202)
async def hermes_feedback_endpoint(
    payload: HermesFeedback,
    _: bool = Depends(_verify_service_token),
):
    """接收 Hermes skill 執行後的回饋訊號（L4 學習閉環入口）。"""
    try:
        await persist_feedback(payload)
    except Exception as e:  # noqa: BLE001
        logger.warning("persist_feedback failed (swallowed): %s", e)
    return {
        "accepted": True,
        "session_id": payload.session_id,
        "skill_name": payload.skill_name,
    }
