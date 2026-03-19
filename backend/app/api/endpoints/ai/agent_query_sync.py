"""
Agent 同步問答 API 端點（非串流）

供外部系統（OpenClaw、LINE Bot、MCP）透過 HTTP 呼叫的同步問答端點。
回傳完整 JSON 回應而非 SSE 串流。

Version: 1.2.0
Created: 2026-03-02
Updated: 2026-03-02 - v1.2.0 安全修復 R2（auth 強化 + timeout + log 過濾）
"""

import asyncio
import hmac
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.dependencies import get_async_db
from app.core.rate_limiter import limiter
from app.schemas.ai.rag import AgentQueryRequest, AgentSyncResponse
from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post(
    "/agent/query",
    response_model=AgentSyncResponse,
    summary="Agent 同步問答（非串流）",
)
@limiter.limit("10/minute")
async def agent_query_sync(
    request: Request,
    body: AgentQueryRequest,
    response: Response,
    _auth: bool = Depends(_verify_service_token),
    db: AsyncSession = Depends(get_async_db),
) -> AgentSyncResponse:
    """
    同步問答端點 — 收集完整回答後一次回傳。

    認證方式: X-Service-Token header（設定 MCP_SERVICE_TOKEN 環境變數啟用）
    未設定 token 時僅在 DEVELOPMENT_MODE=true 且來源為 localhost 時放行。
    """
    # v5.0: NemoClaw 代理人
    from app.services.ai.nemoclaw_agent import NemoClawAgent

    agent = NemoClawAgent(db)

    answer_tokens = []
    sources = []
    tools_used = []
    latency_ms = 0

    async def _collect_response():
        nonlocal latency_ms
        async for event_str in agent.stream_query(
            question=body.question,
            history=body.history,
            session_id=body.session_id,
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
                return AgentSyncResponse(
                    success=False,
                    error=event.get("error", "未知錯誤"),
                    latency_ms=latency_ms,
                )
        return None

    try:
        error_response = await asyncio.wait_for(
            _collect_response(), timeout=get_ai_config().agent_sync_query_timeout
        )
        if error_response:
            return error_response

        return AgentSyncResponse(
            success=True,
            answer="".join(answer_tokens),
            sources=sources,
            tools_used=tools_used,
            latency_ms=latency_ms,
        )

    except asyncio.TimeoutError:
        logger.warning("Agent sync query timed out after %ds", get_ai_config().agent_sync_query_timeout)
        return AgentSyncResponse(
            success=False,
            error=f"查詢逾時（{get_ai_config().agent_sync_query_timeout} 秒）",
        )
    except Exception as e:
        logger.error("Agent sync query failed: %s", e, exc_info=True)
        return AgentSyncResponse(
            success=False,
            error="查詢處理失敗，請稍後重試",
        )
