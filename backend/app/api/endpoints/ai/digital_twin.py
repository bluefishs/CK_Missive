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
import re
import time

from fastapi import APIRouter, Depends, HTTPException
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


_JOB_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _validate_job_id(job_id: str) -> str:
    """驗證 job_id 格式，防止路徑穿越攻擊"""
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    return job_id


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
    _validate_job_id(job_id)
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
    _validate_job_id(job_id)
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
            resp = await client.get(
                f"{gateway_url.rstrip('/')}/tasks/{job_id}",
                headers=headers,
            )
            if resp.status_code >= 400:
                return {"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"}
            return resp.json()
    except Exception as e:
        logger.error("Task status proxy error: %s", e)
        return {"success": False, "error": "任務狀態查詢失敗"}


async def _proxy_task_action(
    job_id: str, action: str, body: dict
) -> dict:
    """共用代理函數 — 轉發 approve/reject 至 OpenClaw"""
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
            resp = await client.post(
                f"{gateway_url.rstrip('/')}/tasks/{job_id}/{action}",
                json=body,
                headers=headers,
            )
            if resp.status_code >= 400:
                return {"success": False, "error": f"上游服務回應 HTTP {resp.status_code}"}
            return resp.json()
    except Exception as e:
        logger.error("Task %s proxy error: %s", action, e)
        return {"success": False, "error": f"任務{action}操作失敗"}


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

        base_url = f"{gateway_url.rstrip('/')}/events"

        try:
            timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "GET", base_url, params={"channel": channel}, headers=headers,
                ) as resp:
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
            yield _sse_event({"type": "error", "error": "即時轉播連線中斷"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/digital-twin/agent-topology")
async def agent_topology(
    _current_user: User = Depends(require_auth()),
):
    """
    Agent 組織圖資料 (V-3.1) — 聚合 NemoClaw Registry + Missive Agent Roles

    回傳結構化的 Agent 節點與邊資料，供前端 React Flow 渲染組織圖。
    """
    import os

    nodes = []
    edges = []

    # ── 1. NemoClaw 節點 (Leader / Orchestrator) ──
    nodes.append({
        "id": "nemoclaw",
        "type": "leader",
        "label": "NemoClaw 監控塔",
        "description": "Gateway + Registry + Scheduler + Health Probe",
        "status": "unknown",
        "capabilities": ["gateway", "registry", "scheduler", "health_probe"],
        "project": "CK_NemoClaw",
    })

    # ── 2. OpenClaw 節點 (Engine + Leader Agent) ──
    nodes.append({
        "id": "openclaw",
        "type": "engine",
        "label": "OpenClaw 通用引擎",
        "description": "Multi-Agent + Memory + Leader Agent 編排",
        "status": "unknown",
        "capabilities": ["reason", "delegate", "event_relay", "memory"],
        "project": "CK_OpenClaw",
    })
    edges.append({
        "source": "nemoclaw",
        "target": "openclaw",
        "label": "gateway → engine",
        "type": "delegation",
    })

    # ── 3. Missive Agent Roles ──
    try:
        from app.services.ai.agent_roles import get_all_role_profiles

        for ctx, profile in get_all_role_profiles().items():
            node_id = f"missive-{ctx}"
            nodes.append({
                "id": node_id,
                "type": "role",
                "label": profile.identity,
                "description": ", ".join(profile.capabilities[:4]),
                "status": "active",
                "capabilities": list(profile.capabilities),
                "project": "CK_Missive",
                "context": ctx,
            })
            edges.append({
                "source": "openclaw",
                "target": node_id,
                "label": f"delegate → {ctx}",
                "type": "delegation",
            })
    except Exception as e:
        logger.warning("Failed to load agent roles: %s", e)

    # ── 4. 外部專案 Agent ──
    external_agents = [
        {
            "id": "ck-lvrland",
            "label": "地政圖資引擎",
            "description": "地籍查詢, 公告現值, 都更, 空間分析",
            "capabilities": ["map_rendering", "spatial_analysis", "land_query"],
            "project": "CK_lvrland_Webmap",
            "triggers": ["地圖", "測繪", "圖資", "地籍", "土地"],
        },
        {
            "id": "ck-tunnel",
            "label": "隧道監測引擎",
            "description": "裂縫偵測, 感測器監控, 點雲分析",
            "capabilities": ["sensor_monitoring", "crack_detection", "alert_management"],
            "project": "CK_DigitalTunnel",
            "triggers": ["隧道", "感測", "監控", "裂縫"],
        },
    ]

    for agent in external_agents:
        nodes.append({
            "id": agent["id"],
            "type": "plugin",
            "label": agent["label"],
            "description": agent["description"],
            "status": "unknown",
            "capabilities": agent["capabilities"],
            "project": agent["project"],
            "triggers": agent.get("triggers", []),
        })
        edges.append({
            "source": "openclaw",
            "target": agent["id"],
            "label": f"delegate → {agent['id']}",
            "type": "delegation",
        })

    # ── 5. KG Hub 連線 ──
    edges.append({
        "source": "ck-lvrland",
        "target": "missive-knowledge-graph",
        "label": "federated-contribute",
        "type": "data_flow",
    })
    edges.append({
        "source": "ck-tunnel",
        "target": "missive-knowledge-graph",
        "label": "federated-contribute",
        "type": "data_flow",
    })

    # ── 6. 嘗試從 NemoClaw Registry 取得即時狀態 ──
    try:
        from app.services.ai.federation_client import get_federation_client

        client = get_federation_client()
        systems = client.list_available_systems()

        status_map = {s["id"]: s.get("status", "unknown") for s in systems}
        for node in nodes:
            nid = str(node["id"])
            if nid in status_map:
                node["status"] = status_map[nid]
            elif nid.startswith("missive-"):
                node["status"] = "active"
    except Exception as e:
        logger.debug("Registry status probe failed: %s", e)

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }


@router.get("/digital-twin/qa-impact")
async def qa_impact_analysis(
    base_branch: str = "main",
    _current_user: User = Depends(require_auth()),
):
    """
    Diff-aware QA 影響分析 (V-3.3) — 分析 git diff 識別受影響模組

    回傳受影響的前後端模組、建議測試範圍，供前端顯示或自動觸發 QA。
    """
    import os
    import subprocess

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )

    try:
        # 取得相對 base branch 的變更檔案
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_branch}"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception as e:
        return {"success": False, "error": f"Git diff failed: {e}", "affected": []}

    if not changed_files:
        return {
            "success": True,
            "changed_files_count": 0,
            "affected": [],
            "recommendation": "no_changes",
            "message": "沒有偵測到變更，無需 QA",
        }

    # ── 分類變更 ──
    backend_changes = [f for f in changed_files if f.startswith("backend/")]
    frontend_changes = [f for f in changed_files if f.startswith("frontend/")]
    other_changes = [f for f in changed_files if not f.startswith(("backend/", "frontend/"))]

    affected_modules: list[dict] = []

    # 後端影響分析
    backend_categories = {
        "api": [], "services": [], "models": [], "schemas": [],
        "migrations": [], "tests": [], "config": [],
    }
    for f in backend_changes:
        if "/api/endpoints/" in f:
            backend_categories["api"].append(f)
        elif "/services/" in f:
            backend_categories["services"].append(f)
        elif "/models/" in f:
            backend_categories["models"].append(f)
        elif "/schemas/" in f:
            backend_categories["schemas"].append(f)
        elif "/alembic/" in f:
            backend_categories["migrations"].append(f)
        elif "/tests/" in f:
            backend_categories["tests"].append(f)
        else:
            backend_categories["config"].append(f)

    for cat, files in backend_categories.items():
        if files:
            affected_modules.append({
                "layer": "backend",
                "category": cat,
                "files": files[:10],
                "count": len(files),
                "risk": "high" if cat in ("models", "migrations", "api") else "medium",
            })

    # 前端影響分析
    frontend_categories = {
        "pages": [], "components": [], "hooks": [], "api": [],
        "types": [], "tests": [], "config": [],
    }
    for f in frontend_changes:
        if "/pages/" in f:
            frontend_categories["pages"].append(f)
        elif "/components/" in f:
            frontend_categories["components"].append(f)
        elif "/hooks/" in f:
            frontend_categories["hooks"].append(f)
        elif "/api/" in f:
            frontend_categories["api"].append(f)
        elif "/types/" in f:
            frontend_categories["types"].append(f)
        elif "/__tests__/" in f or ".test." in f:
            frontend_categories["tests"].append(f)
        else:
            frontend_categories["config"].append(f)

    for cat, files in frontend_categories.items():
        if files:
            affected_modules.append({
                "layer": "frontend",
                "category": cat,
                "files": files[:10],
                "count": len(files),
                "risk": "high" if cat in ("pages", "api", "types") else "medium",
            })

    # 風險評估
    high_risk = sum(1 for m in affected_modules if m["risk"] == "high")
    has_migrations = bool(backend_categories["migrations"])
    has_model_changes = bool(backend_categories["models"])

    if has_migrations or has_model_changes:
        recommendation = "full_qa"
        message = "偵測到 DB 模型/遷移變更，建議執行完整 QA"
    elif high_risk >= 3:
        recommendation = "full_qa"
        message = f"偵測到 {high_risk} 個高風險模組變更，建議完整 QA"
    elif high_risk >= 1:
        recommendation = "diff_aware_qa"
        message = f"偵測到 {high_risk} 個高風險模組，建議 diff-aware QA"
    else:
        recommendation = "quick_qa"
        message = "僅低風險變更，快速 QA 即可"

    return {
        "success": True,
        "changed_files_count": len(changed_files),
        "affected": affected_modules,
        "recommendation": recommendation,
        "message": message,
        "summary": {
            "backend_changes": len(backend_changes),
            "frontend_changes": len(frontend_changes),
            "other_changes": len(other_changes),
            "high_risk_modules": high_risk,
            "has_migrations": has_migrations,
        },
        "suggested_commands": {
            "full": "/qa-smart full",
            "diff_aware": "/qa-smart",
            "quick": "/qa-smart quick",
        },
    }


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
