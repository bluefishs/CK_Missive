"""
Digital Twin 代理端點 — 透過後端代理 NemoClaw Gateway

前端無法直接呼叫 NemoClaw Gateway (CORS + X-Service-Token 認證)，
因此透過本端點代理請求，由 FederationClient 處理認證與通訊。

流程:
  前端 → POST /ai/digital-twin/query/stream → FederationClient.delegate_auto()
       → NemoClaw Gateway (含 X-Service-Token) → SSE 回傳前端

Version: 1.0.0
Created: 2026-03-22
"""

import json
import logging
import time

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.core.dependencies import require_auth
from app.extended.models import User
from app.api.sse_utils import SSE_HEADERS
from app.schemas.ai.digital_twin import (
    DigitalTwinQueryRequest,
    TaskApprovalRequest,
    TaskRejectionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/digital-twin/query/stream")
async def digital_twin_query_stream(
    request: DigitalTwinQueryRequest,
    current_user: User = Depends(require_auth()),
) -> StreamingResponse:
    """
    數位分身串流查詢 — 代理至 NemoClaw Gateway

    SSE 事件格式 (與 Agent 串流相容):
      data: {"type":"status","message":"..."}
      data: {"type":"token","token":"..."}
      data: {"type":"done","latency_ms":N,"model":"nemoclaw-gateway"}
      data: {"type":"error","error":"..."}
    """

    async def event_generator():
        start_ms = time.monotonic()

        # Status: 連線中
        yield _sse_event({
            "type": "status",
            "message": "正在連接數位分身...",
        })

        try:
            from app.services.ai.federation_client import get_federation_client

            client = get_federation_client()

            # Status: 推理中
            yield _sse_event({
                "type": "status",
                "message": "正在透過 NemoClaw Gateway 推理...",
            })

            # 優先走 delegate 路徑（經 NemoClaw 排程器 → ck-missive 插件）
            # 若 delegate 失敗（插件離線），回退至 query_external(openclaw)
            result = await client.delegate(
                target_agent_id="ck-missive",
                intent=request.question,
                context={
                    "session_id": request.session_id or "",
                    "user": current_user.username if current_user else "anonymous",
                    **(request.context or {}),
                },
                timeout=60.0,
            )

            # delegate 成功時，從 target_response 提取純文字答案
            # target_response 結構: {success, result: {answer: "...", model, sources}, meta, ...}
            if result.get("success") and result.get("target_response"):
                target_resp = result["target_response"]
                if isinstance(target_resp, dict):
                    # 嘗試多層提取: result.answer > answer > text
                    inner_result = target_resp.get("result", {})
                    if isinstance(inner_result, dict):
                        result["answer"] = inner_result.get("answer", "")
                    if not result.get("answer"):
                        result["answer"] = (
                            target_resp.get("answer", "")
                            or target_resp.get("text", "")
                        )
                    # 提取延遲與模型資訊
                    inner_meta = target_resp.get("meta", {})
                    if isinstance(inner_meta, dict) and inner_meta.get("latency_ms"):
                        result["latency_ms"] = inner_meta["latency_ms"]
                elif isinstance(target_resp, str):
                    result["answer"] = target_resp

            elapsed_ms = int((time.monotonic() - start_ms) * 1000)

            if result.get("success"):
                answer = result.get("answer", "")

                if answer:
                    yield _sse_event({"type": "token", "token": answer})
                else:
                    yield _sse_event({
                        "type": "token",
                        "token": "數位分身已處理請求，但未回傳文字答案。",
                    })

                yield _sse_event({
                    "type": "done",
                    "latency_ms": result.get("latency_ms", elapsed_ms),
                    "model": "nemoclaw-gateway",
                    "tools_used": result.get("tools_used", []),
                })
            else:
                error_msg = result.get("error", "數位分身處理失敗")
                logger.warning(
                    "Digital twin delegate failed: %s (latency=%dms)",
                    error_msg,
                    result.get("latency_ms", 0),
                )
                yield _sse_event({
                    "type": "error",
                    "error": error_msg,
                    "code": "DELEGATE_FAILED",
                })
                yield _sse_event({
                    "type": "done",
                    "latency_ms": elapsed_ms,
                    "model": "nemoclaw-gateway",
                })

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_ms) * 1000)
            logger.error("Digital twin proxy error: %s", e, exc_info=True)
            yield _sse_event({
                "type": "error",
                "error": f"數位分身連線失敗: {type(e).__name__}",
                "code": "SERVICE_ERROR",
            })
            yield _sse_event({
                "type": "done",
                "latency_ms": elapsed_ms,
                "model": "nemoclaw-gateway",
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )



@router.post("/digital-twin/tasks/{job_id}/approve")
async def approve_task(
    job_id: str,
    request: TaskApprovalRequest,
    current_user: User = Depends(require_auth()),
):
    """
    代理審批 — 轉發至 OpenClaw POST /tasks/{job_id}/approve

    Human Approval Gate (V-2.1): 允許前端使用者核准敏感操作。
    """
    return await _proxy_task_action(
        job_id,
        "approve",
        {"approved_by": request.approved_by or current_user.username},
    )


@router.post("/digital-twin/tasks/{job_id}/reject")
async def reject_task(
    job_id: str,
    request: TaskRejectionRequest,
    current_user: User = Depends(require_auth()),
):
    """
    代理拒絕 — 轉發至 OpenClaw POST /tasks/{job_id}/reject

    Human Approval Gate (V-2.1): 允許前端使用者拒絕敏感操作。
    """
    return await _proxy_task_action(
        job_id,
        "reject",
        {
            "rejected_by": request.rejected_by or current_user.username,
            "reason": request.reason,
        },
    )


@router.get("/digital-twin/tasks/{job_id}")
async def get_task_status(
    job_id: str,
    _current_user: User = Depends(require_auth()),
):
    """代理查詢任務狀態 — 轉發至 OpenClaw GET /tasks/{job_id}"""
    import os

    try:
        import httpx
    except ImportError:
        return {"success": False, "error": "httpx not installed"}

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{gateway_url.rstrip('/')}/tasks/{job_id}",
                headers=headers,
            )
            return resp.json()
    except Exception as e:
        logger.error("Task status proxy error: %s", e)
        return {"success": False, "error": str(e)}


async def _proxy_task_action(
    job_id: str, action: str, body: dict
) -> dict:
    """共用代理函數 — 轉發 approve/reject 至 OpenClaw"""
    import os

    try:
        import httpx
    except ImportError:
        return {"success": False, "error": "httpx not installed"}

    gateway_url = os.getenv("NEMOCLAW_GATEWAY_URL", "http://nemoclaw_tower:9000")
    token = os.getenv("MCP_SERVICE_TOKEN", "")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["X-Service-Token"] = token

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{gateway_url.rstrip('/')}/tasks/{job_id}/{action}",
                json=body,
                headers=headers,
            )
            return resp.json()
    except Exception as e:
        logger.error("Task %s proxy error: %s", action, e)
        return {"success": False, "error": str(e)}


@router.get("/digital-twin/live-activity/stream")
async def live_activity_stream(
    channel: str = "jobs",
    _current_user: User = Depends(require_auth()),
) -> StreamingResponse:
    """
    即時 Swarm 轉播 (V-2.2) — 代理 OpenClaw EventRelay SSE 串流

    前端透過 EventSource 訂閱此端點，即時接收 Agent 任務生命週期事件：
    job_completed, job_failed, job_approved, job_rejected 等。

    使用方式: new EventSource('/api/ai/digital-twin/live-activity/stream?channel=jobs')
    """
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

        url = f"{gateway_url.rstrip('/')}/events?channel={channel}"

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code != 200:
                        yield _sse_event({
                            "type": "error",
                            "error": f"EventRelay HTTP {resp.status_code}",
                        })
                        return

                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
                        elif line.startswith(":"):
                            yield f"{line}\n\n"
        except Exception as e:
            logger.warning("Live activity stream error: %s", e)
            yield _sse_event({"type": "error", "error": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/digital-twin/health")
async def digital_twin_health():
    """檢查 NemoClaw Gateway 可達性"""
    try:
        from app.services.ai.federation_client import get_federation_client

        client = get_federation_client()
        systems = client.list_available_systems()

        gateway_found = any(
            s["id"] in ("openclaw", "nemoclaw") for s in systems
        )

        return {
            "available": gateway_found,
            "systems": systems,
            "discovery_source": client._discovery_source if hasattr(client, "_discovery_source") else "unknown",
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }
