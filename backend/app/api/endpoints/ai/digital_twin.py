"""
Digital Twin 代理端點 — 透過後端代理 NemoClaw Gateway

前端無法直接呼叫 NemoClaw Gateway (CORS + X-Service-Token 認證)，
因此透過本端點代理請求，由 FederationClient 處理認證與通訊。

流程:
  前端 → POST /ai/digital-twin/query/stream → FederationClient.delegate_auto()
       → NemoClaw Gateway (含 X-Service-Token) → SSE 回傳前端

Version: 2.0.0 (Service 層提取)
Created: 2026-03-22
Updated: 2026-03-25 — topology/qa-impact/dashboard 委派至 DigitalTwinService
"""

import json
import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.api.sse_utils import SSE_HEADERS
from app.schemas.ai.digital_twin import (
    DigitalTwinQueryRequest,
    TaskApprovalRequest,
    TaskRejectionRequest,
)
from app.services.ai.digital_twin_service import DigitalTwinService

logger = logging.getLogger(__name__)

router = APIRouter()

_JOB_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _validate_job_id(job_id: str) -> str:
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    return job_id


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── V-2.0: SSE Query Stream (本地優先) ─────────────────────

@router.post("/digital-twin/query/stream")
async def digital_twin_query_stream(
    request: DigitalTwinQueryRequest,
    current_user: User = Depends(require_auth()),
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    """
    數位分身串流查詢 — 本地 NemoClawAgent 優先

    v2.0: 直接呼叫本地 Agent（消除 ck-missive→ck-missive 自我循環委派）。
    與 /agent/query/stream 共用同一引擎，但透過 Digital Twin UI 呈現。
    """
    from app.services.ai.nemoclaw_agent import NemoClawAgent
    from app.api.sse_utils import create_sse_response

    agent = NemoClawAgent(db)

    return create_sse_response(
        stream_fn=lambda: agent.stream_query(
            question=request.question,
            history=[],
            session_id=request.session_id or "",
            context=request.context or {},
        ),
        endpoint_name="DigitalTwin",
        done_extra={"model": "nemoclaw-local", "tools_used": [], "iterations": 0},
    )


# ── V-2.1: Task Approval Gate ──────────────────────────────

@router.post("/digital-twin/tasks/{job_id}/approve")
async def approve_task(
    job_id: str, request: TaskApprovalRequest,
    current_user: User = Depends(require_auth()),
):
    """代理審批 — 轉發至 OpenClaw"""
    _validate_job_id(job_id)
    return await _proxy_task_action(job_id, "approve", {"approved_by": request.approved_by or current_user.username})


@router.post("/digital-twin/tasks/{job_id}/reject")
async def reject_task(
    job_id: str, request: TaskRejectionRequest,
    current_user: User = Depends(require_auth()),
):
    """代理拒絕 — 轉發至 OpenClaw"""
    _validate_job_id(job_id)
    return await _proxy_task_action(job_id, "reject", {
        "rejected_by": request.rejected_by or current_user.username, "reason": request.reason,
    })


@router.post("/digital-twin/tasks/{job_id}")
async def get_task_status(job_id: str, _current_user: User = Depends(require_auth())):
    """代理查詢任務狀態"""
    _validate_job_id(job_id)
    import os
    try:
        import httpx
    except ImportError:
        return {"success": False, "error": "後端缺少必要套件"}

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{gateway_url.rstrip('/')}/tasks/{job_id}", headers=headers)
            if resp.status_code >= 400:
                return {"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"}
            return resp.json()
    except Exception as e:
        logger.error("Task status proxy error: %s", e)
        return {"success": False, "error": "任務狀態查詢失敗"}


# ── V-2.2: Live Activity Stream ────────────────────────────

@router.get("/digital-twin/live-activity/stream")
async def live_activity_stream(
    channel: str = "jobs", _current_user: User = Depends(require_auth()),
) -> StreamingResponse:
    """即時 Swarm 轉播 — 代理 OpenClaw EventRelay SSE"""
    import os
    allowed_channels = {"jobs", "agents"}
    if channel not in allowed_channels:
        channel = "jobs"

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    async def event_generator():
        try:
            import httpx
        except ImportError:
            yield _sse_event({"type": "error", "error": "httpx not installed"})
            return

        headers: dict[str, str] = {"Accept": "text/event-stream"}
        if token:
            headers["X-Service-Token"] = token

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", f"{gateway_url.rstrip('/')}/events",
                                         params={"channel": channel}, headers=headers) as resp:
                    if resp.status_code != 200:
                        yield _sse_event({"type": "error", "error": f"EventRelay HTTP {resp.status_code}"})
                        return
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") or line.startswith(":"):
                            yield f"{line}\n\n"
        except Exception as e:
            logger.warning("Live activity stream error: %s", e)
            yield _sse_event({"type": "error", "error": "即時轉播連線中斷"})

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── V-3.1: Agent Topology (委派 Service) ───────────────────

@router.post("/digital-twin/agent-topology")
async def agent_topology(_current_user: User = Depends(require_auth())):
    """Agent 組織圖資料 — 委派至 DigitalTwinService"""
    return await DigitalTwinService.build_topology()


# ── V-3.3: QA Impact (委派 Service) ────────────────────────

@router.post("/digital-twin/qa-impact")
async def qa_impact_analysis(
    base_branch: str = "main", _current_user: User = Depends(require_auth()),
):
    """Diff-aware QA 影響分析 — 委派至 DigitalTwinService"""
    return await DigitalTwinService.analyze_qa_impact(base_branch)


# ── V-4.0: Dashboard Snapshot (新增) ───────────────────────

@router.post("/digital-twin/dashboard")
async def dashboard_snapshot(
    db: AsyncSession = Depends(get_async_db),
    _current_user: User = Depends(require_auth()),
):
    """聚合分身狀態快照 — profile + capability + daily + health"""
    return await DigitalTwinService.get_dashboard_snapshot(db)


# ── Health Check ───────────────────────────────────────────

@router.post("/digital-twin/health")
async def digital_twin_health():
    """
    數位分身健康狀態 — 本地能力 + Gateway 可達性

    本地 Agent 永遠可用；Gateway 為可選增強。
    """
    # 本地能力（永遠回傳）
    local_roles = []
    try:
        from app.services.ai.agent_roles import get_all_role_profiles
        local_roles = list(get_all_role_profiles().keys())
    except Exception:
        pass

    health = {
        "local_agent": True,
        "local_roles": local_roles,
        "local_roles_count": len(local_roles),
        "gateway_available": False,
        "gateway_systems": [],
    }

    # Gateway（可選）
    try:
        from app.services.ai.federation_client import get_federation_client
        client = get_federation_client()
        systems = client.list_available_systems()
        health["gateway_available"] = any(s["id"] in ("openclaw", "nemoclaw") for s in systems)
        health["gateway_systems"] = systems
    except Exception as e:
        health["gateway_error"] = str(e)

    return health


# ── Shared Helper ──────────────────────────────────────────

async def _proxy_task_action(job_id: str, action: str, body: dict) -> dict:
    import os
    try:
        import httpx
    except ImportError:
        return {"success": False, "error": "後端缺少必要套件"}

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{gateway_url.rstrip('/')}/tasks/{job_id}/{action}", json=body, headers=headers)
            if resp.status_code >= 400:
                return {"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"}
            return resp.json()
    except Exception as e:
        logger.error("Task %s proxy error: %s", action, e)
        return {"success": False, "error": f"任務{action}操作失敗"}
