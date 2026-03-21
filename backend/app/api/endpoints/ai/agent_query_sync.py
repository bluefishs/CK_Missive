"""
Agent 同步問答 API 端點（非串流）

供外部系統（OpenClaw、LINE Bot、MCP）透過 HTTP 呼叫的同步問答端點。
回傳完整 JSON 回應而非 SSE 串流。

支援雙格式：
  - v0 (legacy): { question, history?, session_id?, context? }
  - v1 (Schema v1.0): { agent_id, action, payload, timestamp, ... }

Version: 2.0.0
Created: 2026-03-02
Updated: 2026-03-20 - v2.0.0 P1-b-2 Schema v1.0 雙格式相容
"""

import asyncio
import hmac
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.dependencies import get_async_db
from app.core.rate_limiter import limiter
from app.schemas.ai.rag import (
    AgentQueryRequest,
    AgentSyncResponse,
    AgentV1ErrorObject,
    AgentV1Meta,
    AgentV1ReasonResult,
    AgentV1Response,
    detect_request_format,
)
from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

router = APIRouter()

# 回應方代理人 ID
_RESPONDER_AGENT_ID = "ck_missive"


def _verify_service_token(
    request: Request,
    x_service_token: Optional[str] = Header(None),
):
    """驗證服務 Token（內部系統間呼叫）"""
    expected_token = os.getenv("MCP_SERVICE_TOKEN")

    if not expected_token:
        # 未設定 token：僅在開發模式下允許 localhost
        is_dev = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        client_host = request.client.host if request.client else ""
        if is_dev and client_host in ("127.0.0.1", "::1"):
            return True
        raise HTTPException(status_code=403, detail="Service token required")

    if not x_service_token or not hmac.compare_digest(
        x_service_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Invalid service token")

    return True


def _build_v1_success(
    action: str,
    answer: str,
    sources: list,
    tools_used: list,
    latency_ms: int,
    request_id: str,
) -> Dict[str, Any]:
    """建構 Schema v1.0 成功回應 dict。"""
    return AgentV1Response(
        success=True,
        agent_id=_RESPONDER_AGENT_ID,
        action=action,
        result=AgentV1ReasonResult(
            answer=answer,
            sources=sources,
            tools_used=tools_used,
        ),
        meta=AgentV1Meta(latency_ms=latency_ms, request_id=request_id),
    ).model_dump()


def _build_v1_error(
    action: str,
    code: str,
    message: str,
    latency_ms: int = 0,
    request_id: str = "",
) -> Dict[str, Any]:
    """建構 Schema v1.0 錯誤回應 dict。"""
    return AgentV1Response(
        success=False,
        agent_id=_RESPONDER_AGENT_ID,
        action=action,
        error=AgentV1ErrorObject(code=code, message=message),
        meta=AgentV1Meta(latency_ms=latency_ms, request_id=request_id),
    ).model_dump()


@router.post(
    "/agent/query",
    response_model=None,
    summary="Agent 同步問答（非串流，支援 v0/v1 雙格式）",
)
@limiter.limit("10/minute")
async def agent_query_sync(
    request: Request,
    response: Response,
    _auth: bool = Depends(_verify_service_token),
    db: AsyncSession = Depends(get_async_db),
):
    """
    同步問答端點 — 收集完整回答後一次回傳。

    自動偵測請求格式：
      - v0 (legacy): 頂層含 question → 回傳 AgentSyncResponse
      - v1 (Schema v1.0): 含 agent_id + action + payload + timestamp → 回傳 AgentV1Response 信封

    認證方式: X-Service-Token header（設定 MCP_SERVICE_TOKEN 環境變數啟用）
    未設定 token 時僅在 DEVELOPMENT_MODE=true 且來源為 localhost 時放行。
    """
    # --- 1) 解析 raw body，偵測格式 ---
    try:
        raw_body: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    fmt = detect_request_format(raw_body)
    request_id = str(uuid.uuid4())

    # --- 2) 提取參數 ---
    if fmt == "v1":
        # Schema v1.0 格式
        payload = raw_body.get("payload", {})
        question = payload.get("question", "")
        history = payload.get("context", {}).get("history") if isinstance(payload.get("context"), dict) else None
        session_id = raw_body.get("session_id")
        action = raw_body.get("action", "query")

        if not question:
            return JSONResponse(
                status_code=422,
                content=_build_v1_error(
                    action=action,
                    code="INVALID_SCHEMA",
                    message="payload.question is required",
                    request_id=request_id,
                ),
            )
    else:
        # v0 legacy 格式 — 驗證
        try:
            body = AgentQueryRequest(**raw_body)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))
        question = body.question
        history = body.history
        session_id = body.session_id
        action = "query"

    # --- 3) 執行 Agent 查詢 ---
    from app.services.ai.nemoclaw_agent import NemoClawAgent

    agent = NemoClawAgent(db)

    answer_tokens: list[str] = []
    sources: list[Dict[str, Any]] = []
    tools_used: list[str] = []
    latency_ms = 0

    async def _collect_response():
        nonlocal latency_ms
        async for event_str in agent.stream_query(
            question=question,
            history=history,
            session_id=session_id,
        ):
            if not event_str.startswith("data: "):
                continue
            try:
                event = json.loads(event_str[6:])
            except (json.JSONDecodeError, IndexError):
                continue

            event_type = event.get("type")
            if event_type == "token":
                answer_tokens.append(event.get("token", ""))
            elif event_type == "sources":
                sources.extend(event.get("sources", []))
            elif event_type == "tool_result":
                tool = event.get("tool", "")
                if tool:
                    tools_used.append(tool)
            elif event_type == "done":
                latency_ms = event.get("latency_ms", 0)
            elif event_type == "error":
                error_msg = event.get("error", "未知錯誤")
                if fmt == "v1":
                    return _build_v1_error(
                        action=action,
                        code="INTERNAL_ERROR",
                        message=error_msg,
                        latency_ms=latency_ms,
                        request_id=request_id,
                    )
                return AgentSyncResponse(
                    success=False,
                    error=error_msg,
                    latency_ms=latency_ms,
                )
        return None

    try:
        error_response = await asyncio.wait_for(
            _collect_response(), timeout=get_ai_config().agent_sync_query_timeout
        )
        if error_response:
            if fmt == "v1":
                return JSONResponse(content=error_response)
            return error_response

        answer = "".join(answer_tokens)

        if fmt == "v1":
            return JSONResponse(content=_build_v1_success(
                action=action,
                answer=answer,
                sources=sources,
                tools_used=tools_used,
                latency_ms=latency_ms,
                request_id=request_id,
            ))

        return AgentSyncResponse(
            success=True,
            answer=answer,
            sources=sources,
            tools_used=tools_used,
            latency_ms=latency_ms,
        )

    except asyncio.TimeoutError:
        timeout_s = get_ai_config().agent_sync_query_timeout
        logger.warning("Agent sync query timed out after %ds", timeout_s)
        if fmt == "v1":
            return JSONResponse(
                status_code=504,
                content=_build_v1_error(
                    action=action,
                    code="TIMEOUT",
                    message=f"查詢逾時（{timeout_s} 秒）",
                    request_id=request_id,
                ),
            )
        return AgentSyncResponse(
            success=False,
            error=f"查詢逾時（{timeout_s} 秒）",
        )
    except Exception as e:
        logger.error("Agent sync query failed: %s", e, exc_info=True)
        if fmt == "v1":
            return JSONResponse(
                status_code=500,
                content=_build_v1_error(
                    action=action,
                    code="INTERNAL_ERROR",
                    message="查詢處理失敗，請稍後重試",
                    request_id=request_id,
                ),
            )
        return AgentSyncResponse(
            success=False,
            error="查詢處理失敗，請稍後重試",
        )
