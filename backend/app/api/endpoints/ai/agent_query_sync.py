"""
Agent 同步問答 API 端點（非串流）

供外部系統（OpenClaw、LINE Bot、MCP、Telegram）透過 HTTP 呼叫的同步問答端點。
回傳完整 JSON 回應而非 SSE 串流。

支援雙格式：
  - v0 (legacy): { question, history?, session_id?, context?, channel? }
  - v1 (Schema v1.0): { agent_id, action, payload, timestamp, ... }

增強功能 (v3.0.0):
  - channel 來源追蹤 (line/telegram/openclaw/mcp/web/discord/hermes)
  - capabilities 能力探索
  - metadata 回應後設資料
  - session_handoff 跨會話上下文注入
  - 結構化 error_code 錯誤回應

Version: 3.0.0
Created: 2026-03-02
Updated: 2026-04-05 - v3.0.0 channel tracking + capabilities + metadata + handoff
"""

import asyncio
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.dependencies import get_async_db
from app.core.rate_limiter import limiter
from app.core.service_auth import require_scope
from app.schemas.ai.rag import (
    AgentQueryRequest,
    AgentSyncCapabilities,
    AgentSyncMetadata,
    AgentSyncResponse,
    AgentV1ErrorObject,
    AgentV1Meta,
    AgentV1ReasonResult,
    AgentV1Response,
    detect_request_format,
)
from app.services.ai.core.ai_config import get_ai_config

logger = logging.getLogger(__name__)

router = APIRouter()

# 回應方代理人 ID
_RESPONDER_AGENT_ID = "ck_missive"

# Agent 版本 (與 schema 預設值對齊)
_AGENT_VERSION = "5.5.0"

# 支援的業務領域
_DOMAINS = [
    "document", "dispatch", "project", "vendor",
    "finance", "tender", "knowledge_graph",
]


def _verify_service_token(
    request: Request,
    x_service_token: Optional[str] = Header(None),
):
    """驗證服務 Token（內部系統間呼叫）

    支援雙 token 輪替: MCP_SERVICE_TOKEN (current) + MCP_SERVICE_TOKEN_PREV (previous)
    """
    current_token = os.getenv("MCP_SERVICE_TOKEN")
    prev_token = os.getenv("MCP_SERVICE_TOKEN_PREV")

    if not current_token:
        # 未設定 token：僅在開發模式下允許 localhost
        is_dev = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        client_host = request.client.host if request.client else ""
        if is_dev and client_host in ("127.0.0.1", "::1"):
            logger.warning(
                "MCP_SERVICE_TOKEN not configured — allowing localhost bypass "
                "(DEVELOPMENT_MODE=true). This MUST NOT occur in production."
            )
            return True
        raise HTTPException(status_code=403, detail="Service token required")

    if not x_service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")

    token_bytes = x_service_token.encode("utf-8")
    match_current = hmac.compare_digest(token_bytes, current_token.encode("utf-8"))
    match_prev = (
        hmac.compare_digest(token_bytes, prev_token.encode("utf-8"))
        if prev_token
        else False
    )
    if not match_current and not match_prev:
        raise HTTPException(status_code=401, detail="Invalid service token")

    return True


def _get_tool_names(limit: int = 15) -> List[str]:
    """取得 Agent 可用工具名稱清單（安全降級）"""
    try:
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        return registry.get_tool_names_by_priority(top_n=limit)
    except Exception:
        logger.debug("Failed to load tool registry for capabilities", exc_info=True)
        return []


def _build_capabilities() -> Dict[str, Any]:
    """建構 Agent 能力清單"""
    return AgentSyncCapabilities(
        tools=_get_tool_names(limit=15),
        vision=True,
        voice=True,
        domains=_DOMAINS,
    ).model_dump()


def _build_metadata(
    latency_ms: int,
    tools_used: List[str],
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """建構回應後設資料"""
    return AgentSyncMetadata(
        model="gemma4",
        latency_ms=latency_ms,
        tools_used=tools_used,
        source_channel=channel,
        agent_version=_AGENT_VERSION,
    ).model_dump()


def _build_v1_success(
    action: str,
    answer: str,
    sources: list,
    tools_used: list,
    latency_ms: int,
    request_id: str,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """建構 Schema v1.0 成功回應 dict（含增強 meta）。"""
    return AgentV1Response(
        success=True,
        agent_id=_RESPONDER_AGENT_ID,
        action=action,
        result=AgentV1ReasonResult(
            answer=answer,
            sources=sources,
            tools_used=tools_used,
        ),
        meta=AgentV1Meta(
            latency_ms=latency_ms,
            request_id=request_id,
            model="gemma4",
            source_channel=channel,
            agent_version=_AGENT_VERSION,
        ),
    ).model_dump()


def _build_v1_error(
    action: str,
    code: str,
    message: str,
    latency_ms: int = 0,
    request_id: str = "",
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """建構 Schema v1.0 錯誤回應 dict（含增強 meta）。"""
    return AgentV1Response(
        success=False,
        agent_id=_RESPONDER_AGENT_ID,
        action=action,
        error=AgentV1ErrorObject(code=code, message=message),
        meta=AgentV1Meta(
            latency_ms=latency_ms,
            request_id=request_id,
            source_channel=channel,
            agent_version=_AGENT_VERSION,
        ),
    ).model_dump()


async def _try_inject_handoff(
    session_id: Optional[str],
    history: Optional[list],
) -> Optional[list]:
    """嘗試注入 session handoff 上下文。

    若 session_id 存在且有 handoff 資料，將其作為 system 訊息
    注入至 history 開頭，並清除 handoff（消費後即刪）。
    """
    if not session_id:
        return history

    try:
        from app.services.ai.agent.agent_conversation_memory import ConversationMemory
        memory = ConversationMemory()
        handoff = await memory.get_session_handoff(session_id)
        if not handoff:
            return history

        # 建構 handoff system message
        topic = handoff.get("active_topic", "")
        key_entities = handoff.get("key_entities", [])
        pending = handoff.get("pending_questions", [])

        parts = ["[Session Handoff]"]
        if topic:
            parts.append(f"上次話題: {topic}")
        if key_entities:
            parts.append(f"關鍵實體: {', '.join(key_entities[:10])}")
        if pending:
            parts.append(f"未解問題: {'; '.join(pending[:3])}")

        handoff_msg = {"role": "system", "content": " | ".join(parts)}

        # 消費 handoff
        await memory.clear_session_handoff(session_id)
        logger.info("Session handoff injected for session=%s, topic=%s", session_id, topic)

        # 注入至 history 開頭
        injected = [handoff_msg] + (history or [])
        return injected

    except Exception as e:
        logger.debug("Session handoff injection skipped: %s", e)
        return history


@router.post(
    "/agent/query",
    response_model=None,
    summary="Agent 同步問答（非串流，支援 v0/v1 雙格式 + 能力探索 + 頻道追蹤）",
)
@limiter.limit("10/minute")
async def agent_query_sync(
    request: Request,
    response: Response,
    _auth: bool = Depends(require_scope("read:agent")),
    db: AsyncSession = Depends(get_async_db),
):
    """
    同步問答端點 — 收集完整回答後一次回傳。

    自動偵測請求格式：
      - v0 (legacy): 頂層含 question → 回傳 AgentSyncResponse
      - v1 (Schema v1.0): 含 agent_id + action + payload + timestamp → 回傳 AgentV1Response 信封

    v3.0.0 增強：
      - channel: 來源頻道追蹤 (line/telegram/openclaw/mcp/web/discord/hermes)
      - capabilities: Agent 能力探索（工具/Vision/Voice/領域）
      - metadata: 回應後設資料（模型/延遲/版本）
      - session_handoff: 跨會話上下文自動注入
      - error_code: 結構化錯誤碼

    認證方式: X-Service-Token header（設定 MCP_SERVICE_TOKEN 環境變數啟用）
    未設定 token 時僅在 DEVELOPMENT_MODE=true 且來源為 localhost 時放行。
    """
    start_time = time.monotonic()

    # --- 1) 解析 raw body，偵測格式 ---
    try:
        raw_body: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    fmt = detect_request_format(raw_body)
    request_id = str(uuid.uuid4())

    # --- 2) 提取參數 ---
    channel: Optional[str] = None

    if fmt == "v1":
        # Schema v1.0 格式
        payload = raw_body.get("payload", {})
        question = payload.get("question", "")
        history = payload.get("context", {}).get("history") if isinstance(payload.get("context"), dict) else None
        session_id = raw_body.get("session_id")
        action = raw_body.get("action", "query")
        channel = payload.get("channel") or raw_body.get("channel")

        if not question:
            return JSONResponse(
                status_code=422,
                content=_build_v1_error(
                    action=action,
                    code="INVALID_SCHEMA",
                    message="payload.question is required",
                    request_id=request_id,
                    channel=channel,
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
        channel = body.channel
        action = "query"

    # --- 3) Session handoff 注入 ---
    history = await _try_inject_handoff(session_id, history)

    # --- 4) 執行 Agent 查詢 ---
    from app.services.ai.misc.missive_agent import MissiveAgent

    agent = MissiveAgent(db)

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
                        channel=channel,
                    )
                return AgentSyncResponse(
                    success=False,
                    answer=error_msg,
                    error=error_msg,
                    error_code="internal",
                    tools_used=tools_used,
                    latency_ms=latency_ms,
                    metadata=AgentSyncMetadata(
                        model="gemma4",
                        latency_ms=latency_ms,
                        tools_used=tools_used,
                        source_channel=channel,
                        agent_version=_AGENT_VERSION,
                    ),
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

        # 計算實際延遲（若 SSE 未回報）
        if not latency_ms:
            latency_ms = int((time.monotonic() - start_time) * 1000)

        # Shadow trace — 統一 helper (provider auto-resolve + X-Hermes-Session)
        from app.services.ai.agent.shadow_helpers import fire_shadow_trace
        asyncio.create_task(fire_shadow_trace(
            request=request,
            channel=channel,
            question=question,
            answer=answer,
            success=True,
            latency_ms=latency_ms,
            tools_used=tools_used,
            sources_count=len(sources),
            session_id=session_id,
        ))

        if fmt == "v1":
            return JSONResponse(content=_build_v1_success(
                action=action,
                answer=answer,
                sources=sources,
                tools_used=tools_used,
                latency_ms=latency_ms,
                request_id=request_id,
                channel=channel,
            ))

        return AgentSyncResponse(
            success=True,
            answer=answer,
            sources=sources,
            tools_used=tools_used,
            latency_ms=latency_ms,
            capabilities=AgentSyncCapabilities(
                tools=_get_tool_names(limit=15),
                vision=True,
                voice=True,
                domains=_DOMAINS,
            ),
            metadata=AgentSyncMetadata(
                model="gemma4",
                latency_ms=latency_ms,
                tools_used=tools_used,
                source_channel=channel,
                agent_version=_AGENT_VERSION,
            ),
        )

    except asyncio.TimeoutError:
        timeout_s = get_ai_config().agent_sync_query_timeout
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.warning("Agent sync query timed out after %ds", timeout_s)
        from app.services.ai.agent.shadow_helpers import fire_shadow_trace
        asyncio.create_task(fire_shadow_trace(
            request=request, channel=channel, question=question, answer="",
            success=False, latency_ms=elapsed_ms, error_code="timeout",
            session_id=session_id,
        ))
        if fmt == "v1":
            return JSONResponse(
                status_code=504,
                content=_build_v1_error(
                    action=action,
                    code="TIMEOUT",
                    message=f"查詢逾時（{timeout_s} 秒）",
                    latency_ms=elapsed_ms,
                    request_id=request_id,
                    channel=channel,
                ),
            )
        return AgentSyncResponse(
            success=False,
            answer=f"查詢逾時（{timeout_s} 秒），請稍後重試或簡化問題",
            error=f"查詢逾時（{timeout_s} 秒）",
            error_code="timeout",
            tools_used=tools_used,
            latency_ms=elapsed_ms,
            metadata=AgentSyncMetadata(
                model="gemma4",
                latency_ms=elapsed_ms,
                tools_used=tools_used,
                source_channel=channel,
                agent_version=_AGENT_VERSION,
            ),
        )
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        logger.error("Agent sync query failed: %s", e, exc_info=True)
        from app.services.ai.agent.shadow_helpers import fire_shadow_trace
        asyncio.create_task(fire_shadow_trace(
            request=request, channel=channel, question=question, answer="",
            success=False, latency_ms=elapsed_ms, error_code="internal",
            session_id=session_id,
        ))
        if fmt == "v1":
            return JSONResponse(
                status_code=500,
                content=_build_v1_error(
                    action=action,
                    code="INTERNAL_ERROR",
                    message="查詢處理失敗，請稍後重試",
                    latency_ms=elapsed_ms,
                    request_id=request_id,
                    channel=channel,
                ),
            )
        return AgentSyncResponse(
            success=False,
            answer="查詢處理失敗，請稍後重試",
            error="查詢處理失敗，請稍後重試",
            error_code="internal",
            tools_used=[],
            latency_ms=elapsed_ms,
            metadata=AgentSyncMetadata(
                model="gemma4",
                latency_ms=elapsed_ms,
                tools_used=[],
                source_channel=channel,
                agent_version=_AGENT_VERSION,
            ),
        )
